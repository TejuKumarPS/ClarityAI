import inspect
from unittest.mock import MagicMock, patch
import pytest
import pydantic
import openai

from app.llm.models import ActionItem, AIAnalysis, LLMUsage, LLMResponse
from app.llm.base import LLMProvider
from app.llm.fake_provider import FakeLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.exceptions import (
    LLMError,
    LLMConfigurationError,
    LLMInputTooLargeError,
    LLMResponseValidationError,
    LLMProviderError,
)
import app.processing.stages.ai_analysis as ai_analysis_module


# ==========================================
# 1. Model Validation Tests
# ==========================================

def test_ai_analysis_valid_construction():
    analysis = AIAnalysis(
        summary="Quarterly planning meeting.",
        key_points=["Budget approved", "Hiring targets established"],
        action_items=[
            ActionItem(task="Publish roadmaps", owner="Rahul"),
            ActionItem(task="Finalize budget spreadsheet", owner=None),
        ],
        sentiment="positive",
    )
    assert analysis.summary == "Quarterly planning meeting."
    assert len(analysis.key_points) == 2
    assert len(analysis.action_items) == 2
    assert analysis.action_items[1].owner is None
    assert analysis.sentiment == "positive"


@pytest.mark.parametrize("sentiment", ["positive", "neutral", "negative", "mixed"])
def test_ai_analysis_allowed_sentiments(sentiment):
    analysis = AIAnalysis(
        summary="Summary text.",
        key_points=["Point 1"],
        action_items=[],
        sentiment=sentiment,
    )
    assert analysis.sentiment == sentiment


def test_ai_analysis_invalid_sentiment_raises():
    with pytest.raises(pydantic.ValidationError):
        AIAnalysis(
            summary="Summary text.",
            key_points=["Point 1"],
            action_items=[],
            sentiment="ecstatic",  # invalid sentiment
        )


def test_ai_analysis_missing_required_fields_raises():
    with pytest.raises(pydantic.ValidationError):
        AIAnalysis(summary="Only summary")  # type: ignore


def test_ai_analysis_key_points_limit():
    points = [f"Point {i}" for i in range(11)]
    with pytest.raises(pydantic.ValidationError):
        AIAnalysis(
            summary="Summary",
            key_points=points,  # 11 points exceeds max_length=10
            action_items=[],
            sentiment="neutral",
        )


def test_llm_usage_non_negative_validation():
    usage = LLMUsage(input_tokens=100, output_tokens=50, total_tokens=150)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.total_tokens == 150

    # Negative tokens must be rejected
    with pytest.raises(pydantic.ValidationError):
        LLMUsage(input_tokens=-1, output_tokens=10, total_tokens=9)

    with pytest.raises(pydantic.ValidationError):
        LLMUsage(input_tokens=10, output_tokens=-5, total_tokens=5)

    with pytest.raises(pydantic.ValidationError):
        LLMUsage(input_tokens=10, output_tokens=10, total_tokens=-20)


def test_llm_usage_preserves_provider_reported_asymmetric_values():
    # Does not enforce total == input + output, preserving provider-reported values
    usage = LLMUsage(input_tokens=100, output_tokens=50, total_tokens=160)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.total_tokens == 160


def test_llm_response_model():
    analysis = AIAnalysis(
        summary="Summary",
        key_points=["Point 1"],
        action_items=[],
        sentiment="neutral",
    )
    usage = LLMUsage(input_tokens=10, output_tokens=5, total_tokens=15)
    response = LLMResponse(
        analysis=analysis,
        usage=usage,
        provider="openai",
        model="gpt-4o-mini",
    )
    assert response.analysis.summary == "Summary"
    assert response.usage.total_tokens == 15
    assert response.provider == "openai"
    assert response.model == "gpt-4o-mini"


# ==========================================
# 2. FakeLLMProvider Tests
# ==========================================

def test_fake_llm_provider_deterministic_output_and_call_count():
    provider = FakeLLMProvider()
    assert provider.call_count == 0

    result = provider.analyze("Any random transcript content.")
    assert provider.call_count == 1
    assert isinstance(result, LLMResponse)
    assert isinstance(result.analysis, AIAnalysis)
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 50
    assert result.usage.total_tokens == 150
    assert result.provider == "fake"
    assert result.model == "fake-model"

    # Second call increments count
    provider.analyze("Second transcript.")
    assert provider.call_count == 2


# ==========================================
# 3. OpenAIProvider Mocked Tests (No Network)
# ==========================================

def test_openai_provider_missing_api_key_raises():
    provider = OpenAIProvider(api_key="")
    with pytest.raises(LLMConfigurationError) as exc_info:
        provider.analyze("Some transcript")
    assert "OPENAI_API_KEY is not configured" in str(exc_info.value)


def test_openai_provider_input_too_large_raises():
    provider = OpenAIProvider(api_key="sk-mock", max_input_chars=50)
    oversized_text = "A" * 100
    with pytest.raises(LLMInputTooLargeError) as exc_info:
        provider.analyze(oversized_text)
    assert "exceeds limit" in str(exc_info.value)


def test_openai_provider_successful_mocked_parse(monkeypatch):
    mock_parsed_analysis = AIAnalysis(
        summary="Mocked executive summary of meeting.",
        key_points=["Key milestone delivered.", "Q4 goals on track."],
        action_items=[ActionItem(task="Deploy staging environment", owner="Alice")],
        sentiment="positive",
    )

    mock_choice = MagicMock()
    mock_choice.message.refusal = None
    mock_choice.message.parsed = mock_parsed_analysis

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 120
    mock_usage.completion_tokens = 60
    mock_usage.total_tokens = 180

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = mock_usage

    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.return_value = mock_completion

    provider = OpenAIProvider(api_key="sk-mock-valid-key", model="gpt-4o-mini")
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    result = provider.analyze("Executive leadership transcript.")
    assert isinstance(result, LLMResponse)
    assert result.analysis == mock_parsed_analysis
    assert result.analysis.summary == "Mocked executive summary of meeting."
    assert result.usage.input_tokens == 120
    assert result.usage.output_tokens == 60
    assert result.usage.total_tokens == 180
    assert result.provider == "openai"
    assert result.model == "gpt-4o-mini"


def test_openai_provider_authentication_error_mapping(monkeypatch):
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.side_effect = openai.AuthenticationError(
        "Incorrect API key",
        response=MagicMock(status_code=401),
        body=None,
    )

    provider = OpenAIProvider(api_key="sk-mock-bad-key")
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    with pytest.raises(LLMConfigurationError) as exc_info:
        provider.analyze("Transcript text")
    assert "authentication failed" in str(exc_info.value).lower()


def test_openai_provider_timeout_error_mapping(monkeypatch):
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.side_effect = openai.APITimeoutError(
        request=MagicMock()
    )

    provider = OpenAIProvider(api_key="sk-mock")
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    with pytest.raises(LLMProviderError) as exc_info:
        provider.analyze("Transcript text")
    assert "timeout" in str(exc_info.value).lower()


def test_openai_provider_rate_limit_error_mapping(monkeypatch):
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.side_effect = openai.RateLimitError(
        "Rate limit exceeded",
        response=MagicMock(status_code=429),
        body=None,
    )

    provider = OpenAIProvider(api_key="sk-mock")
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    with pytest.raises(LLMProviderError) as exc_info:
        provider.analyze("Transcript text")
    assert "rate limit" in str(exc_info.value).lower()


def test_openai_provider_empty_parsed_response_raises(monkeypatch):
    mock_choice = MagicMock()
    mock_choice.message.refusal = None
    mock_choice.message.parsed = None

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.return_value = mock_completion

    provider = OpenAIProvider(api_key="sk-mock")
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    with pytest.raises(LLMResponseValidationError):
        provider.analyze("Transcript text")


# ==========================================
# 4. Architectural Isolation Test
# ==========================================

def test_ai_analysis_stage_does_not_import_openai():
    source_code = inspect.getsource(ai_analysis_module)
    assert "import openai" not in source_code
    assert "from openai" not in source_code
    # Verify stage only imports LLMProvider
    assert "from app.llm.base import LLMProvider" in source_code
