from app.llm.base import LLMProvider
from app.processing.base import ProcessingStage
from app.processing.models import ProcessingContext
from app.processing.exceptions import InvalidProcessingContextError


class AIAnalysisStage(ProcessingStage):
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "ai_analysis"

    def process(self, context: ProcessingContext) -> ProcessingContext:
        if not context or context.transcript is None:
            raise InvalidProcessingContextError("Context and transcript must not be None")

        analysis = self.provider.analyze(context.transcript)
        context.ai_analysis = analysis
        return context
