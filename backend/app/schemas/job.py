import uuid
from datetime import datetime
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class JobCreateTextRequest(BaseModel):
    input_type: Literal["text_paste"] = Field(
        default="text_paste",
        description="The transcript input type, must be 'text_paste' for JSON submissions",
    )
    content: str = Field(
        ...,
        description="The raw transcript text content",
    )


class JobResponse(BaseModel):
    id: uuid.UUID
    input_type: str
    status: str
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_input_tokens: Optional[int] = None
    llm_output_tokens: Optional[int] = None
    llm_total_tokens: Optional[int] = None
    error_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobListItem(BaseModel):
    id: uuid.UUID
    input_type: str
    status: str
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    created_at: datetime
    processing_started_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_input_tokens: Optional[int] = None
    llm_output_tokens: Optional[int] = None
    llm_total_tokens: Optional[int] = None
    error_code: Optional[str] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    items: list[JobListItem]
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Number of items per page")
    total: int = Field(..., ge=0, description="Total number of jobs")
    pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)

