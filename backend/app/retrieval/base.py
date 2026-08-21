from abc import ABC, abstractmethod
from app.chunking.models import DocumentChunk
from app.retrieval.models import RetrievedChunk


class Retriever(ABC):
    @abstractmethod
    def retrieve(
        self,
        query: str,
        chunks: list[DocumentChunk],
        max_results: int,
    ) -> list[RetrievedChunk]:
        """Retrieve relevant DocumentChunk objects for a query ordered by relevance score."""
        pass
