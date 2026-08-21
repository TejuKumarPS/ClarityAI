from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    index: int = Field(..., ge=0, description="0-based sequential chunk index")
    text: str = Field(..., description="Chunk text content")
    start_char: int = Field(..., ge=0, description="Start character offset (inclusive)")
    end_char: int = Field(..., ge=0, description="End character offset (exclusive)")


class ChunkingMetadata(BaseModel):
    chunk_count: int = Field(..., ge=0)
    chunking_strategy: str = "character"
    chunk_size_chars: int = Field(..., gt=0)
    chunk_overlap_chars: int = Field(..., ge=0)
