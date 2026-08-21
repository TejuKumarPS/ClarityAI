from app.processing.base import ProcessingStage
from app.processing.models import ProcessingContext, TranscriptMetadata
from app.processing.exceptions import InvalidProcessingContextError


class AnalyzeStage(ProcessingStage):
    @property
    def name(self) -> str:
        return "analyze"

    def process(self, context: ProcessingContext) -> ProcessingContext:
        if not context or context.transcript is None:
            raise InvalidProcessingContextError("Context and transcript must not be None")

        text = context.transcript
        char_count = len(text)
        words = [w for w in text.split() if w]
        word_count = len(words)
        lines = [line for line in text.splitlines() if line.strip()]
        line_count = len(lines) if text.strip() else 0

        context.metadata = TranscriptMetadata(
            character_count=char_count,
            word_count=word_count,
            line_count=line_count,
        )
        return context
