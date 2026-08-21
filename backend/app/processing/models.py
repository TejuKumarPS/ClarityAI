from pydantic import BaseModel
from app.llm.models import AIAnalysis


class TranscriptMetadata(BaseModel):
    character_count: int = 0
    word_count: int = 0
    line_count: int = 0


class ProcessingContext(BaseModel):
    job_id: str
    transcript: str
    metadata: TranscriptMetadata | None = None
    ai_analysis: AIAnalysis | None = None


class ProcessingResult(BaseModel):
    processor: str = "clarityai-pipeline"
    version: str = "0.2.0"
    job_id: str
    metadata: TranscriptMetadata
    ai_analysis: AIAnalysis | None = None
