from app.core.config import settings
from app.chunking.base import DocumentChunker
from app.chunking.models import DocumentChunk
from app.chunking.exceptions import (
    InvalidChunkConfigurationError,
    EmptyDocumentError,
)


class CharacterChunker(DocumentChunker):
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        self.chunk_size = chunk_size if chunk_size is not None else settings.CHUNK_SIZE_CHARS
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP_CHARS
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        if self.chunk_size <= 0:
            raise InvalidChunkConfigurationError("chunk_size must be greater than 0")
        if self.chunk_overlap < 0:
            raise InvalidChunkConfigurationError("chunk_overlap must be greater than or equal to 0")
        if self.chunk_overlap >= self.chunk_size:
            raise InvalidChunkConfigurationError("chunk_overlap must be strictly less than chunk_size")

    def chunk(self, text: str) -> list[DocumentChunk]:
        if not text or not text.strip():
            raise EmptyDocumentError("Cannot chunk empty or whitespace-only text")

        text_len = len(text)
        if text_len <= self.chunk_size:
            return [
                DocumentChunk(
                    index=0,
                    text=text,
                    start_char=0,
                    end_char=text_len,
                )
            ]

        stride = self.chunk_size - self.chunk_overlap
        chunks: list[DocumentChunk] = []
        start = 0
        idx = 0

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk_text = text[start:end]
            chunks.append(
                DocumentChunk(
                    index=idx,
                    text=chunk_text,
                    start_char=start,
                    end_char=end,
                )
            )
            if end >= text_len:
                break
            start += stride
            idx += 1

        return chunks
