from app.core.config import settings
from app.llm.base import LLMProvider
from app.chunking.base import DocumentChunker
from app.chunking.chunker import CharacterChunker
from app.retrieval.base import Retriever
from app.retrieval.lexical import KeywordRetriever
from app.processing.base import ProcessingStage
from app.processing.models import ProcessingContext, ProcessingResult, TranscriptMetadata
from app.processing.exceptions import ProcessingError, PipelineExecutionError, InvalidProcessingContextError
from app.processing.stages.normalize import NormalizeStage
from app.processing.stages.analyze import AnalyzeStage
from app.processing.stages.chunk import ChunkStage
from app.processing.stages.retrieve import RetrievalStage
from app.processing.stages.ai_analysis import AIAnalysisStage


class ProcessingPipeline:
    def __init__(self, stages: list[ProcessingStage] | None = None):
        self.stages: list[ProcessingStage] = (
            stages
            if stages is not None
            else [
                NormalizeStage(),
                AnalyzeStage(),
            ]
        )

    def add_stage(self, stage: ProcessingStage) -> "ProcessingPipeline":
        self.stages.append(stage)
        return self

    def process(self, context: ProcessingContext) -> ProcessingResult:
        if not context or not context.job_id or context.transcript is None:
            raise InvalidProcessingContextError("Valid ProcessingContext with job_id and transcript is required")

        current_context = context
        for stage in self.stages:
            try:
                current_context = stage.process(current_context)
            except ProcessingError:
                raise
            except Exception as exc:
                raise PipelineExecutionError(f"Error in stage '{stage.name}': {exc}") from exc

        metadata = current_context.metadata or TranscriptMetadata()
        return ProcessingResult(
            processor="clarityai-pipeline",
            version="0.6.0",
            job_id=current_context.job_id,
            metadata=metadata,
            chunking_metadata=current_context.chunking_metadata,
            retrieval_metadata=current_context.retrieval_metadata,
            ai_analysis=current_context.ai_analysis,
            llm_usage=current_context.llm_usage,
            llm_provider=current_context.llm_provider,
            llm_model=current_context.llm_model,
        )



def create_default_pipeline(
    llm_provider: LLMProvider | None = None,
    chunker: DocumentChunker | None = None,
    retriever: Retriever | None = None,
) -> ProcessingPipeline:
    if llm_provider is not None:
        provider = llm_provider
    elif (
        (getattr(settings, "LLM_PROVIDER", "").lower() == "groq")
        or (getattr(settings, "GROQ_API_KEY", None) and not getattr(settings, "OPENAI_API_KEY", None))
    ):
        from app.llm.groq_provider import GroqProvider
        provider = GroqProvider()
    else:
        from app.llm.openai_provider import OpenAIProvider
        provider = OpenAIProvider()

    doc_chunker = chunker if chunker is not None else CharacterChunker()
    doc_retriever = retriever if retriever is not None else KeywordRetriever()
    return ProcessingPipeline(
        stages=[
            NormalizeStage(),
            AnalyzeStage(),
            ChunkStage(chunker=doc_chunker),
            RetrievalStage(retriever=doc_retriever),
            AIAnalysisStage(provider=provider),
        ]
    )
