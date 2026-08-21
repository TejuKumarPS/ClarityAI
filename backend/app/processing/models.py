from typing import Optional
from pydantic import BaseModel


class TranscriptMetadata(BaseModel):
    character_count: int = 0
    word_count: int = 0
    line_count: int = 0


class ProcessingContext(BaseModel):
    job_id: str
    transcript: str
    metadata: Optional[TranscriptMetadata] = None


class ProcessingResult(BaseModel):
    processor: str = "clarityai-pipeline"
    version: str = "0.1.0"
    job_id: str
    metadata: TranscriptMetadata
