from pydantic import BaseModel, Field
from app.chunking.models import DocumentChunk


class RetrievedChunk(BaseModel):
    chunk: DocumentChunk
    score: float = Field(..., ge=0.0, description="Relevance score in [0.0, 1.0]")


class RetrievalMetadata(BaseModel):
    query: str = Field(..., description="Bounded query representation for privacy and observability")
    retrieved_count: int = Field(..., ge=0)
    retrieval_strategy: str = "keyword"
    max_results: int = Field(..., gt=0)
