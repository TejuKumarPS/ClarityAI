import pytest
from app.llm.models import ActionItem, AIAnalysis, LLMUsage
from app.llm.fake_provider import FakeLLMProvider
from app.processing import (
    ProcessingContext,
    ProcessingResult,
    TranscriptMetadata,
    ProcessingStage,
    ProcessingPipeline,
    create_default_pipeline,
    ProcessingError,
    InvalidProcessingContextError,
    PipelineExecutionError,
)
from app.processing.stages.normalize import NormalizeStage
from app.processing.stages.analyze import AnalyzeStage
from app.processing.stages.ai_analysis import AIAnalysisStage


# ==========================================
# ProcessingContext & Models Tests
# ==========================================

def test_processing_context_initialization():
    context = ProcessingContext(
        job_id="test-job-123",
        transcript="Sample transcript text.",
    )
    assert context.job_id == "test-job-123"
    assert context.transcript == "Sample transcript text."
    assert context.metadata is None
    assert context.ai_analysis is None
    assert context.llm_usage is None
    assert context.llm_provider is None
    assert context.llm_model is None


def test_processing_result_serialization():
    analysis = AIAnalysis(
        summary="Short summary",
        key_points=["Point 1"],
        action_items=[ActionItem(task="Task 1", owner="Alice")],
        sentiment="neutral",
    )
    usage = LLMUsage(input_tokens=100, output_tokens=50, total_tokens=150)
    result = ProcessingResult(
        processor="clarityai-pipeline",
        version="0.3.0",
        job_id="test-job-123",
        metadata=TranscriptMetadata(character_count=20, word_count=3, line_count=1),
        ai_analysis=analysis,
        llm_usage=usage,
        llm_provider="openai",
        llm_model="gpt-4o-mini",
    )
    dumped = result.model_dump()
    assert dumped == {
        "processor": "clarityai-pipeline",
        "version": "0.3.0",
        "job_id": "test-job-123",
        "metadata": {
            "character_count": 20,
            "word_count": 3,
            "line_count": 1,
        },
        "ai_analysis": {
            "summary": "Short summary",
            "key_points": ["Point 1"],
            "action_items": [{"task": "Task 1", "owner": "Alice"}],
            "sentiment": "neutral",
        },
        "llm_usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
        },
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
    }


# ==========================================
# NormalizeStage Tests
# ==========================================

def test_normalize_stage_basic_cleaning():
    stage = NormalizeStage()
    assert stage.name == "normalize"

    context = ProcessingContext(
        job_id="job-1",
        transcript="   \n  Hello World   \n   This is a line.  \n\n  ",
    )
    updated = stage.process(context)
    assert updated.transcript == "Hello World\nThis is a line."


def test_normalize_stage_preserves_meaningful_content():
    stage = NormalizeStage()
    text = "Line 1: Discussed quarterly budget.\nLine 2: Approved marketing spend."
    context = ProcessingContext(job_id="job-1", transcript=text)
    updated = stage.process(context)
    assert updated.transcript == text


def test_normalize_stage_none_transcript_raises():
    stage = NormalizeStage()
    context = ProcessingContext(job_id="job-1", transcript="")
    context.transcript = None  # type: ignore
    with pytest.raises(InvalidProcessingContextError):
        stage.process(context)


# ==========================================
# AnalyzeStage Tests
# ==========================================

def test_analyze_stage_deterministic_statistics():
    stage = AnalyzeStage()
    assert stage.name == "analyze"

    context = ProcessingContext(
        job_id="job-1",
        transcript="hello world",
    )
    updated = stage.process(context)
    assert updated.metadata is not None
    assert updated.metadata.character_count == 11
    assert updated.metadata.word_count == 2
    assert updated.metadata.line_count == 1


def test_analyze_stage_multiline_statistics():
    stage = AnalyzeStage()
    context = ProcessingContext(
        job_id="job-1",
        transcript="Quarterly review meeting.\nAction items assigned to engineering.\nNext sync on Monday.",
    )
    updated = stage.process(context)
    assert updated.metadata is not None
    assert updated.metadata.line_count == 3
    assert updated.metadata.word_count == 12
    assert updated.metadata.character_count == len(context.transcript)


def test_analyze_stage_empty_text():
    stage = AnalyzeStage()
    context = ProcessingContext(job_id="job-1", transcript="")
    updated = stage.process(context)
    assert updated.metadata is not None
    assert updated.metadata.character_count == 0
    assert updated.metadata.word_count == 0
    assert updated.metadata.line_count == 0


# ==========================================
# AIAnalysisStage Tests
# ==========================================

def test_ai_analysis_stage_execution():
    fake_provider = FakeLLMProvider()
    stage = AIAnalysisStage(provider=fake_provider)
    assert stage.name == "ai_analysis"

    context = ProcessingContext(
        job_id="job-ai",
        transcript="Leadership alignment on engineering roadmap.",
    )
    updated = stage.process(context)
    assert updated.ai_analysis is not None
    assert isinstance(updated.ai_analysis, AIAnalysis)
    assert updated.ai_analysis.sentiment == "positive"
    assert len(updated.ai_analysis.key_points) >= 1
    assert updated.llm_usage is not None
    assert updated.llm_usage.total_tokens == 150
    assert updated.llm_provider == "fake"
    assert updated.llm_model == "fake-model"


def test_ai_analysis_stage_none_transcript_raises():
    fake_provider = FakeLLMProvider()
    stage = AIAnalysisStage(provider=fake_provider)
    context = ProcessingContext(job_id="job-ai", transcript="")
    context.transcript = None  # type: ignore
    with pytest.raises(InvalidProcessingContextError):
        stage.process(context)


# ==========================================
# ProcessingPipeline Tests
# ==========================================

def test_pipeline_ordered_execution_with_ai_stage():
    fake_provider = FakeLLMProvider()
    pipeline = create_default_pipeline(llm_provider=fake_provider)

    context = ProcessingContext(
        job_id="pipeline-job-123",
        transcript="   \n  Sprint Retrospective Discussion.  \n  Team velocity was excellent.  \n   ",
    )

    result = pipeline.process(context)
    assert result.processor == "clarityai-pipeline"
    assert result.version == "0.3.0"
    assert result.job_id == "pipeline-job-123"
    assert result.metadata.word_count == 7
    assert result.metadata.line_count == 2
    assert result.ai_analysis is not None
    assert result.ai_analysis.sentiment == "positive"
    assert len(result.ai_analysis.action_items) == 2
    assert result.llm_usage is not None
    assert result.llm_usage.input_tokens == 100
    assert result.llm_usage.output_tokens == 50
    assert result.llm_usage.total_tokens == 150
    assert result.llm_provider == "fake"
    assert result.llm_model == "fake-model"


def test_pipeline_open_closed_stage_extensibility():
    class UppercaseTagStage(ProcessingStage):
        @property
        def name(self) -> str:
            return "uppercase_tag"

        def process(self, context: ProcessingContext) -> ProcessingContext:
            context.transcript = context.transcript.upper()
            return context

    pipeline = ProcessingPipeline(stages=[
        NormalizeStage(),
        UppercaseTagStage(),
        AnalyzeStage(),
    ])

    context = ProcessingContext(job_id="ext-job", transcript="  hello world  ")
    result = pipeline.process(context)
    assert context.transcript == "HELLO WORLD"
    assert result.metadata.word_count == 2
    assert result.metadata.character_count == 11
    assert result.ai_analysis is None
    assert result.llm_usage is None


def test_pipeline_invalid_context_raises():
    pipeline = create_default_pipeline(llm_provider=FakeLLMProvider())
    context = ProcessingContext(job_id="", transcript="")
    with pytest.raises(InvalidProcessingContextError):
        pipeline.process(context)


def test_pipeline_stage_exception_chained():
    class BrokenStage(ProcessingStage):
        @property
        def name(self) -> str:
            return "broken"

        def process(self, context: ProcessingContext) -> ProcessingContext:
            raise ValueError("Underlying stage failure")

    pipeline = ProcessingPipeline(stages=[BrokenStage()])
    context = ProcessingContext(job_id="job-err", transcript="valid text")

    with pytest.raises(PipelineExecutionError) as exc_info:
        pipeline.process(context)

    assert "Error in stage 'broken'" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, ValueError)
