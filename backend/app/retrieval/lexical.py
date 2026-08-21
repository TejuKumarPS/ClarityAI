import re
from app.chunking.models import DocumentChunk
from app.retrieval.base import Retriever
from app.retrieval.models import RetrievedChunk
from app.retrieval.exceptions import (
    InvalidRetrievalQueryError,
    InvalidRetrievalConfigurationError,
)


class KeywordRetriever(Retriever):
    @staticmethod
    def _tokenize(text: str) -> list[str]:
        if not text:
            return []
        return re.findall(r"\b\w+\b", text.lower())

    def retrieve(
        self,
        query: str,
        chunks: list[DocumentChunk],
        max_results: int,
    ) -> list[RetrievedChunk]:
        if not query or not query.strip():
            raise InvalidRetrievalQueryError("Retrieval query cannot be empty or whitespace")

        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            raise InvalidRetrievalQueryError("Retrieval query must contain at least one word token")

        if max_results <= 0:
            raise InvalidRetrievalConfigurationError("max_results must be greater than 0")

        if not chunks:
            return []

        candidates = []
        total_query_terms = len(query_tokens)

        for chunk in chunks:
            chunk_tokens = set(self._tokenize(chunk.text))
            matching_terms = query_tokens.intersection(chunk_tokens)
            score = len(matching_terms) / total_query_terms
            if score > 0.0:
                candidates.append((score, chunk.index, chunk))

        # Sort: descending by score, ascending by chunk.index
        candidates.sort(key=lambda item: (-item[0], item[1]))

        return [
            RetrievedChunk(chunk=chunk, score=score)
            for score, _, chunk in candidates[:max_results]
        ]
