from typing import List, Optional
from app.processing.base import ProcessingStage
from app.processing.models import ProcessingContext, ProcessingResult, TranscriptMetadata
from app.processing.exceptions import ProcessingError, PipelineExecutionError, InvalidProcessingContextError
from app.processing.stages.normalize import NormalizeStage
from app.processing.stages.analyze import AnalyzeStage


class ProcessingPipeline:
    def __init__(self, stages: Optional[List[ProcessingStage]] = None):
        self.stages: List[ProcessingStage] = (
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
            version="0.1.0",
            job_id=current_context.job_id,
            metadata=metadata,
        )


def create_default_pipeline() -> ProcessingPipeline:
    return ProcessingPipeline()
