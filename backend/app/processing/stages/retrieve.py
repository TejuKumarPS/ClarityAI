from app.core.config import settings
from app.retrieval.base import Retriever
from app.retrieval.lexical import KeywordRetriever
from app.retrieval.models import RetrievalMetadata
from app.retrieval.context_builder import build_bounded_context
from app.processing.base import ProcessingStage
from app.processing.models import ProcessingContext
from app.processing.exceptions import InvalidProcessingContextError


class RetrievalStage(ProcessingStage):
    def __init__(
        self,
        retriever: Retriever | None = None,
        max_results: int | None = None,
        max_context_chars: int | None = None,
    ):
        self.retriever = retriever if retriever is not None else KeywordRetriever()
        self.max_results = max_results if max_results is not None else settings.DEFAULT_MAX_RETRIEVAL_RESULTS
        self.max_context_chars = max_context_chars if max_context_chars is not None else settings.MAX_RETRIEVAL_CONTEXT_CHARACTERS

    @property
    def name(self) -> str:
        return "retrieve"

    def process(self, context: ProcessingContext) -> ProcessingContext:
        if not context or context.transcript is None:
            raise InvalidProcessingContextError("Context and transcript must not be None")

        query = context.retrieval_query or context.transcript

        # Privacy bound: never persist the complete long transcript in metadata
        max_q_len = settings.MAX_RETRIEVAL_QUERY_CHARS
        bounded_query = query[:max_q_len] + "..." if len(query) > max_q_len else query

        retrieved = self.retriever.retrieve(
            query=query,
            chunks=context.chunks,
            max_results=self.max_results,
        )

        context.retrieved_chunks = retrieved
        context.retrieval_metadata = RetrievalMetadata(
            query=bounded_query,
            retrieved_count=len(retrieved),
            retrieval_strategy="keyword",
            max_results=self.max_results,
        )
        context.grounded_context = build_bounded_context(
            retrieved,
            max_chars=self.max_context_chars,
        )
        return context
