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

    model_config = ConfigDict(from_attributes=True)

