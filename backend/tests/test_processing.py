import pytest
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


def test_processing_result_serialization():
    result = ProcessingResult(
        processor="clarityai-pipeline",
        version="0.1.0",
        job_id="test-job-123",
        metadata=TranscriptMetadata(character_count=20, word_count=3, line_count=1),
    )
    dumped = result.model_dump()
    assert dumped == {
        "processor": "clarityai-pipeline",
        "version": "0.1.0",
        "job_id": "test-job-123",
        "metadata": {
            "character_count": 20,
            "word_count": 3,
            "line_count": 1,
        },
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
# ProcessingPipeline Tests
# ==========================================

def test_pipeline_ordered_execution():
    pipeline = create_default_pipeline()
    context = ProcessingContext(
        job_id="pipeline-job-123",
        transcript="   \n  Sprint Retrospective Discussion.  \n  Team velocity was excellent.  \n   ",
    )

    result = pipeline.process(context)
    assert result.processor == "clarityai-pipeline"
    assert result.version == "0.1.0"
    assert result.job_id == "pipeline-job-123"
    assert result.metadata.word_count == 7
    assert result.metadata.line_count == 2
    assert result.metadata.character_count == len("Sprint Retrospective Discussion.\nTeam velocity was excellent.")


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


def test_pipeline_invalid_context_raises():
    pipeline = create_default_pipeline()
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
