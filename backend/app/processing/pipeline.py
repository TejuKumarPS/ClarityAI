from app.llm.base import LLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.chunking.base import DocumentChunker
from app.chunking.chunker import CharacterChunker
from app.processing.base import ProcessingStage
from app.processing.models import ProcessingContext, ProcessingResult, TranscriptMetadata
from app.processing.exceptions import ProcessingError, PipelineExecutionError, InvalidProcessingContextError
from app.processing.stages.normalize import NormalizeStage
from app.processing.stages.analyze import AnalyzeStage
from app.processing.stages.chunk import ChunkStage
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
            version="0.4.0",
            job_id=current_context.job_id,
            metadata=metadata,
            chunking_metadata=current_context.chunking_metadata,
            ai_analysis=current_context.ai_analysis,
            llm_usage=current_context.llm_usage,
            llm_provider=current_context.llm_provider,
            llm_model=current_context.llm_model,
        )


def create_default_pipeline(
    llm_provider: LLMProvider | None = None,
    chunker: DocumentChunker | None = None,
) -> ProcessingPipeline:
    provider = llm_provider if llm_provider is not None else OpenAIProvider()
    doc_chunker = chunker if chunker is not None else CharacterChunker()
    return ProcessingPipeline(
        stages=[
            NormalizeStage(),
            AnalyzeStage(),
            ChunkStage(chunker=doc_chunker),
            AIAnalysisStage(provider=provider),
        ]
    )
