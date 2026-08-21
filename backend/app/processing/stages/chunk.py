from app.core.config import settings
from app.chunking.base import DocumentChunker
from app.chunking.chunker import CharacterChunker
from app.chunking.models import ChunkingMetadata
from app.processing.base import ProcessingStage
from app.processing.models import ProcessingContext
from app.processing.exceptions import InvalidProcessingContextError


class ChunkStage(ProcessingStage):
    def __init__(self, chunker: DocumentChunker | None = None):
        self.chunker = chunker if chunker is not None else CharacterChunker()

    @property
    def name(self) -> str:
        return "chunk"

    def process(self, context: ProcessingContext) -> ProcessingContext:
        if not context or context.transcript is None:
            raise InvalidProcessingContextError("Context and transcript must not be None")

        chunks = self.chunker.chunk(context.transcript)
        context.chunks = chunks

        chunk_size = getattr(self.chunker, "chunk_size", settings.CHUNK_SIZE_CHARS)
        chunk_overlap = getattr(self.chunker, "chunk_overlap", settings.CHUNK_OVERLAP_CHARS)

        context.chunking_metadata = ChunkingMetadata(
            chunk_count=len(chunks),
            chunking_strategy="character",
            chunk_size_chars=chunk_size,
            chunk_overlap_chars=chunk_overlap,
        )
        return context
