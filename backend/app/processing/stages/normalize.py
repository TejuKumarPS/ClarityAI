from app.processing.base import ProcessingStage
from app.processing.models import ProcessingContext
from app.processing.exceptions import InvalidProcessingContextError


class NormalizeStage(ProcessingStage):
    @property
    def name(self) -> str:
        return "normalize"

    def process(self, context: ProcessingContext) -> ProcessingContext:
        if not context or context.transcript is None:
            raise InvalidProcessingContextError("Context and transcript must not be None")

        lines = [line.strip() for line in context.transcript.splitlines()]
        cleaned_text = "\n".join(lines).strip()
        context.transcript = cleaned_text
        return context
