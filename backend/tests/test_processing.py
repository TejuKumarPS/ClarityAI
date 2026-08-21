import pytest
from app.llm.models import (
    ActionItem,
    Decision,
    Risk,
    OpenQuestion,
    AIAnalysis,
    LLMUsage,
)
from app.llm.fake_provider import FakeLLMProvider
from app.chunking.models import DocumentChunk, ChunkingMetadata
from app.chunking.chunker import CharacterChunker
from app.retrieval.models import RetrievedChunk, RetrievalMetadata
from app.retrieval.lexical import KeywordRetriever
from app.retrieval.context_builder import NO_CONTEXT_PLACEHOLDER
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
from app.processing.stages.chunk import ChunkStage
from app.processing.stages.retrieve import RetrievalStage
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
    assert context.chunks == []
    assert context.chunking_metadata is None
    assert context.retrieval_query is None
    assert context.retrieved_chunks == []
    assert context.retrieval_metadata is None
    assert context.grounded_context is None
    assert context.ai_analysis is None
    assert context.llm_usage is None
    assert context.llm_provider is None
    assert context.llm_model is None


def test_processing_result_serialization():
    analysis = AIAnalysis(
        summary="Short summary",
        key_points=["Point 1"],
        decisions=[Decision(decision="Migrate to Postgres 18", rationale="HA")],
        action_items=[ActionItem(task="Task 1", owner="Alice")],
        risks=[Risk(description="Failover lag", severity="low")],
        open_questions=[OpenQuestion(question="Who leads testing?", owner="Bob")],
        sentiment="neutral",
    )
    usage = LLMUsage(input_tokens=100, output_tokens=50, total_tokens=150)
    chunking_meta = ChunkingMetadata(
        chunk_count=2,
        chunking_strategy="character",
        chunk_size_chars=4000,
        chunk_overlap_chars=400,
    )
    retrieval_meta = RetrievalMetadata(
        query="project roadmap...",
        retrieved_count=2,
        retrieval_strategy="keyword",
        max_results=5,
    )
    result = ProcessingResult(
        processor="clarityai-pipeline",
        version="0.6.0",
        job_id="test-job-123",
        metadata=TranscriptMetadata(character_count=20, word_count=3, line_count=1),
        chunking_metadata=chunking_meta,
        retrieval_metadata=retrieval_meta,
        ai_analysis=analysis,
        llm_usage=usage,
        llm_provider="openai",
        llm_model="gpt-4o-mini",
    )
    dumped = result.model_dump()
    assert dumped == {
        "processor": "clarityai-pipeline",
        "version": "0.6.0",
        "job_id": "test-job-123",
        "metadata": {
            "character_count": 20,
            "word_count": 3,
            "line_count": 1,
        },
        "chunking_metadata": {
            "chunk_count": 2,
            "chunking_strategy": "character",
            "chunk_size_chars": 4000,
            "chunk_overlap_chars": 400,
        },
        "retrieval_metadata": {
            "query": "project roadmap...",
            "retrieved_count": 2,
            "retrieval_strategy": "keyword",
            "max_results": 5,
        },
        "ai_analysis": {
            "summary": "Short summary",
            "key_points": ["Point 1"],
            "decisions": [{"decision": "Migrate to Postgres 18", "rationale": "HA"}],
            "action_items": [{"task": "Task 1", "owner": "Alice"}],
            "risks": [{"description": "Failover lag", "severity": "low"}],
            "open_questions": [{"question": "Who leads testing?", "owner": "Bob"}],
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
# ChunkStage Tests
# ==========================================

def test_chunk_stage_execution():
    custom_chunker = CharacterChunker(chunk_size=30, chunk_overlap=10)
    stage = ChunkStage(chunker=custom_chunker)
    assert stage.name == "chunk"

    text = "Sprint Planning Meeting: Deliverables defined for release 2.0 and infrastructure readiness."
    context = ProcessingContext(job_id="job-chunk", transcript=text)

    updated = stage.process(context)
    assert len(updated.chunks) > 1
    assert updated.chunking_metadata is not None
    assert updated.chunking_metadata.chunk_count == len(updated.chunks)
    assert updated.chunking_metadata.chunk_size_chars == 30
    assert updated.chunking_metadata.chunk_overlap_chars == 10
    assert updated.chunking_metadata.chunking_strategy == "character"


def test_chunk_stage_none_transcript_raises():
    stage = ChunkStage()
    context = ProcessingContext(job_id="job-chunk-err", transcript="")
    context.transcript = None  # type: ignore
    with pytest.raises(InvalidProcessingContextError):
        stage.process(context)


# ==========================================
# RetrievalStage Tests
# ==========================================

def test_retrieval_stage_execution():
    retriever = KeywordRetriever()
    stage = RetrievalStage(retriever=retriever, max_results=3)
    assert stage.name == "retrieve"

    chunks = [
        DocumentChunk(index=0, text="Database indexing and optimization roadmap.", start_char=0, end_char=43),
        DocumentChunk(index=1, text="Frontend UI design components in Figma.", start_char=43, end_char=82),
    ]
    context = ProcessingContext(
        job_id="job-ret",
        transcript="Database query optimization guidelines.",
        chunks=chunks,
    )

    updated = stage.process(context)
    assert len(updated.retrieved_chunks) == 1
    assert updated.retrieved_chunks[0].chunk.index == 0
    assert updated.retrieval_metadata is not None
    assert updated.retrieval_metadata.retrieved_count == 1
    assert updated.retrieval_metadata.retrieval_strategy == "keyword"
    assert updated.retrieval_metadata.max_results == 3
    assert "[Chunk 0]" in updated.grounded_context


def test_retrieval_stage_none_transcript_raises():
    stage = RetrievalStage()
    context = ProcessingContext(job_id="job-ret-err", transcript="")
    context.transcript = None  # type: ignore
    with pytest.raises(InvalidProcessingContextError):
        stage.process(context)


# ==========================================
# AIAnalysisStage Tests
# ==========================================

def test_ai_analysis_stage_execution_with_grounded_context():
    fake_provider = FakeLLMProvider()
    received_inputs = []
    orig_analyze = fake_provider.analyze

    def mock_analyze(input_text):
        received_inputs.append(input_text)
        return orig_analyze(input_text)

    fake_provider.analyze = mock_analyze
    stage = AIAnalysisStage(provider=fake_provider)
    assert stage.name == "ai_analysis"

    context = ProcessingContext(
        job_id="job-ai",
        transcript="Original transcript text.",
        grounded_context="[Chunk 0]\nRetrieved grounded chunk text.",
    )
    updated = stage.process(context)
    assert updated.ai_analysis is not None
    assert isinstance(updated.ai_analysis, AIAnalysis)
    assert updated.ai_analysis.sentiment == "positive"
    assert len(updated.ai_analysis.key_points) >= 1
    assert len(updated.ai_analysis.decisions) >= 1
    assert len(updated.ai_analysis.action_items) >= 1
    assert len(updated.ai_analysis.risks) >= 1
    assert len(updated.ai_analysis.open_questions) >= 1
    assert updated.llm_usage is not None
    assert updated.llm_usage.total_tokens == 150
    assert updated.llm_provider == "fake"
    assert updated.llm_model == "fake-model"
    # Grounded context passed to LLM
    assert received_inputs == ["[Chunk 0]\nRetrieved grounded chunk text."]


def test_ai_analysis_stage_never_falls_back_to_transcript_when_grounded_context_set():
    fake_provider = FakeLLMProvider()
    received_inputs = []
    orig_analyze = fake_provider.analyze

    def mock_analyze(input_text):
        received_inputs.append(input_text)
        return orig_analyze(input_text)

    fake_provider.analyze = mock_analyze
    stage = AIAnalysisStage(provider=fake_provider)

    context = ProcessingContext(
        job_id="job-zero-retrieval",
        transcript="CONFIDENTIAL_FULL_TRANSCRIPT_CONTENT_NEVER_SEND",
        grounded_context=NO_CONTEXT_PLACEHOLDER,
    )
    stage.process(context)

    assert len(received_inputs) == 1
    assert received_inputs[0] == NO_CONTEXT_PLACEHOLDER
    assert "CONFIDENTIAL" not in received_inputs[0]


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

def test_pipeline_ordered_execution_5_stages():
    fake_provider = FakeLLMProvider()
    chunker = CharacterChunker(chunk_size=40, chunk_overlap=10)
    retriever = KeywordRetriever()
    pipeline = create_default_pipeline(
        llm_provider=fake_provider,
        chunker=chunker,
        retriever=retriever,
    )

    # Verify stage ordering
    stage_names = [s.name for s in pipeline.stages]
    assert stage_names == ["normalize", "analyze", "chunk", "retrieve", "ai_analysis"]

    context = ProcessingContext(
        job_id="pipeline-job-123",
        transcript="   \n  Sprint Retrospective Discussion.  \n  Team velocity was excellent and deliverables were on time.  \n   ",
    )

    result = pipeline.process(context)
    assert result.processor == "clarityai-pipeline"
    assert result.version == "0.6.0"
    assert result.job_id == "pipeline-job-123"
    assert result.metadata.word_count == 12
    assert result.metadata.line_count == 2
    assert result.chunking_metadata is not None
    assert result.chunking_metadata.chunk_count > 1
    assert result.retrieval_metadata is not None
    assert result.retrieval_metadata.retrieved_count >= 1
    assert result.ai_analysis is not None
    assert result.ai_analysis.sentiment == "positive"
    assert len(result.ai_analysis.decisions) >= 1
    assert len(result.ai_analysis.action_items) >= 1
    assert len(result.ai_analysis.risks) >= 1
    assert len(result.ai_analysis.open_questions) >= 1
    assert result.llm_usage is not None
    assert result.llm_usage.total_tokens == 150
    # Exactly one LLM call despite multiple chunks and retrieval
    assert fake_provider.call_count == 1


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
    assert result.chunking_metadata is None
    assert result.retrieval_metadata is None


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
