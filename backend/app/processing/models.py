from pydantic import BaseModel, Field
from app.llm.models import AIAnalysis, LLMUsage
from app.chunking.models import DocumentChunk, ChunkingMetadata


class TranscriptMetadata(BaseModel):
    character_count: int = 0
    word_count: int = 0
    line_count: int = 0


class ProcessingContext(BaseModel):
    job_id: str
    transcript: str
    metadata: TranscriptMetadata | None = None
    chunks: list[DocumentChunk] = Field(default_factory=list)
    chunking_metadata: ChunkingMetadata | None = None
    ai_analysis: AIAnalysis | None = None
    llm_usage: LLMUsage | None = None
    llm_provider: str | None = None
    llm_model: str | None = None


class ProcessingResult(BaseModel):
    processor: str = "clarityai-pipeline"
    version: str = "0.4.0"
    job_id: str
    metadata: TranscriptMetadata
    chunking_metadata: ChunkingMetadata | None = None
    ai_analysis: AIAnalysis | None = None
    llm_usage: LLMUsage | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
