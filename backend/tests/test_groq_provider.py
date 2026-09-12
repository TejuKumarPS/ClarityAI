import json
from unittest.mock import MagicMock, patch
import pytest
import openai

from app.core.config import Settings
from app.llm.groq_provider import GroqProvider
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMInputTooLargeError,
    LLMResponseValidationError,
    LLMProviderError,
)
from app.processing.pipeline import create_default_pipeline


VALID_AI_ANALYSIS_DICT = {
    "summary": "The team aligned on the Q3 product roadmap and resolved key architectural blockers.",
    "key_points": [
        "Database migration is scheduled for Saturday night.",
        "Frontend team completed the upload UI overhaul."
    ],
    "decisions": [
        {"decision": "Adopt PostgreSQL 16 partition pruning", "rationale": "Improved query latencies"}
    ],
    "action_items": [
        {"task": "Run performance load tests", "owner": "Alex"}
    ],
    "risks": [
        {"description": "Potential downtime during index reconstruction", "severity": "low"}
    ],
    "open_questions": [
        {"question": "Who will monitor the deployment window?", "owner": "Lead Engineer"}
    ],
    "sentiment": "positive"
}


def _make_mock_choice(content: str, refusal: str | None = None):
    choice = MagicMock()
    choice.message.content = content
    choice.message.refusal = refusal
    return choice


def _make_mock_completion(content: str, refusal: str | None = None, prompt_tokens: int = 120, completion_tokens: int = 85):
    completion = MagicMock()
    completion.choices = [_make_mock_choice(content, refusal)]
    completion.usage.prompt_tokens = prompt_tokens
    completion.usage.completion_tokens = completion_tokens
    completion.usage.total_tokens = prompt_tokens + completion_tokens
    return completion


def test_groq_missing_api_key_raises_configuration_error():
    provider = GroqProvider(api_key="", model="llama-3.3-70b-versatile", llm_enabled=True)
    with pytest.raises(LLMConfigurationError, match="GROQ_API_KEY is not configured"):
        provider.analyze("Valid transcript content for meeting analysis")


def test_groq_disabled_raises_configuration_error():
    provider = GroqProvider(api_key="gsk_valid_key", model="llama-3.3-70b-versatile", llm_enabled=False)
    with pytest.raises(LLMConfigurationError, match="LLM processing is disabled"):
        provider.analyze("Valid transcript content for meeting analysis")


def test_groq_input_too_large_raises_error():
    provider = GroqProvider(api_key="gsk_valid_key", max_input_chars=50, llm_enabled=True)
    with pytest.raises(LLMInputTooLargeError, match="exceeds limit"):
        provider.analyze("A" * 51)


def test_groq_valid_json_response_parsed_successfully():
    provider = GroqProvider(api_key="gsk_valid_key", model="llama-3.3-70b-versatile", llm_enabled=True)
    raw_json = json.dumps(VALID_AI_ANALYSIS_DICT)

    mock_completion = _make_mock_completion(raw_json, prompt_tokens=150, completion_tokens=90)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch.object(provider, "_get_client", return_value=mock_client):
        response = provider.analyze("Team discussed roadmap.")

    assert response.provider == "groq"
    assert response.model == "llama-3.3-70b-versatile"
    assert response.analysis.summary == VALID_AI_ANALYSIS_DICT["summary"]
    assert len(response.analysis.key_points) == 2
    assert response.analysis.decisions[0].decision == "Adopt PostgreSQL 16 partition pruning"
    assert response.analysis.sentiment == "positive"
    assert response.usage.input_tokens == 150
    assert response.usage.output_tokens == 90
    assert response.usage.total_tokens == 240


def test_groq_markdown_code_fenced_json_stripped_and_parsed():
    provider = GroqProvider(api_key="gsk_valid_key", model="llama-3.3-70b-versatile", llm_enabled=True)
    fenced_json = f"```json\n{json.dumps(VALID_AI_ANALYSIS_DICT)}\n```"

    mock_completion = _make_mock_completion(fenced_json)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch.object(provider, "_get_client", return_value=mock_client):
        response = provider.analyze("Team discussed roadmap.")

    assert response.analysis.summary == VALID_AI_ANALYSIS_DICT["summary"]


def test_groq_empty_response_raises_validation_error():
    provider = GroqProvider(api_key="gsk_valid_key", llm_enabled=True)
    mock_completion = _make_mock_completion("")
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(LLMResponseValidationError, match="empty structured output"):
            provider.analyze("Transcript context")


def test_groq_refusal_raises_validation_error():
    provider = GroqProvider(api_key="gsk_valid_key", llm_enabled=True)
    mock_completion = _make_mock_completion("", refusal="Safety violation")
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(LLMResponseValidationError, match="Model refused analysis"):
            provider.analyze("Transcript context")


def test_groq_invalid_json_raises_validation_error():
    provider = GroqProvider(api_key="gsk_valid_key", llm_enabled=True)
    mock_completion = _make_mock_completion("{not valid json syntax")
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(LLMResponseValidationError, match="violates AIAnalysis schema"):
            provider.analyze("Transcript context")


def test_groq_missing_required_fields_raises_validation_error():
    provider = GroqProvider(api_key="gsk_valid_key", llm_enabled=True)
    bad_dict = {"summary": "Only a summary, missing key_points and sentiment"}
    mock_completion = _make_mock_completion(json.dumps(bad_dict))
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(LLMResponseValidationError, match="violates AIAnalysis schema"):
            provider.analyze("Transcript context")


def test_groq_auth_error_raises_configuration_error():
    provider = GroqProvider(api_key="gsk_invalid", llm_enabled=True)
    mock_client = MagicMock()
    req = openai._models.FinalRequestOptions.construct(method="post", url="/chat/completions")
    mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
        "Invalid API Key", response=MagicMock(status_code=401), body=None
    )

    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(LLMConfigurationError, match="Groq authentication failed"):
            provider.analyze("Transcript context")


def test_groq_rate_limit_raises_provider_error():
    provider = GroqProvider(api_key="gsk_valid", llm_enabled=True)
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = openai.RateLimitError(
        "TPM exceeded", response=MagicMock(status_code=429), body=None
    )

    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(LLMProviderError, match="Groq rate limit"):
            provider.analyze("Transcript context")


def test_groq_timeout_raises_provider_error():
    provider = GroqProvider(api_key="gsk_valid", llm_enabled=True)
    mock_client = MagicMock()
    req = MagicMock()
    mock_client.chat.completions.create.side_effect = openai.APITimeoutError(request=req)

    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(LLMProviderError, match="Groq network/timeout"):
            provider.analyze("Transcript context")


def test_create_default_pipeline_selects_groq_when_groq_key_set():
    with patch("app.processing.pipeline.settings") as mock_settings:
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.GROQ_API_KEY = "gsk_auto_detected_key"
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GROQ_MODEL = "llama-3.3-70b-versatile"
        mock_settings.GROQ_BASE_URL = "https://api.groq.com/openai/v1"
        mock_settings.MAX_LLM_INPUT_CHARACTERS = 100000
        mock_settings.LLM_REQUEST_TIMEOUT_SECONDS = 60.0
        mock_settings.LLM_MAX_RETRY_ATTEMPTS = 3
        mock_settings.LLM_ENABLED = True

        pipeline = create_default_pipeline()
        ai_stage = pipeline.stages[-1]
        assert isinstance(ai_stage.provider, GroqProvider)


def test_create_default_pipeline_selects_groq_when_provider_is_groq():
    with patch("app.processing.pipeline.settings") as mock_settings:
        mock_settings.LLM_PROVIDER = "groq"
        mock_settings.GROQ_API_KEY = "gsk_provider_key"
        mock_settings.OPENAI_API_KEY = "sk-some-openai-key"
        mock_settings.GROQ_MODEL = "llama-3.3-70b-versatile"
        mock_settings.GROQ_BASE_URL = "https://api.groq.com/openai/v1"
        mock_settings.MAX_LLM_INPUT_CHARACTERS = 100000
        mock_settings.LLM_REQUEST_TIMEOUT_SECONDS = 60.0
        mock_settings.LLM_MAX_RETRY_ATTEMPTS = 3
        mock_settings.LLM_ENABLED = True

        pipeline = create_default_pipeline()
        ai_stage = pipeline.stages[-1]
        assert isinstance(ai_stage.provider, GroqProvider)
