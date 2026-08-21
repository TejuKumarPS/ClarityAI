from abc import ABC, abstractmethod
from app.chunking.models import DocumentChunk


class DocumentChunker(ABC):
    @abstractmethod
    def chunk(self, text: str) -> list[DocumentChunk]:
        """Split input text into an ordered list of deterministic DocumentChunk objects."""
        pass
