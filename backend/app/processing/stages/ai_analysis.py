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

        # Grounded context invariant: use bounded retrieval context whenever set
        input_text = (
            context.grounded_context
            if context.grounded_context is not None
            else context.transcript
        )

        response = self.provider.analyze(input_text)
        context.ai_analysis = response.analysis
        context.llm_usage = response.usage
        context.llm_provider = response.provider
        context.llm_model = response.model
        return context
