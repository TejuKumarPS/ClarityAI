import uuid
from datetime import datetime
from typing import Literal
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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
