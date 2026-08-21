from typing import Literal
from pydantic import BaseModel, Field

SentimentType = Literal["positive", "neutral", "negative", "mixed"]


class ActionItem(BaseModel):
    task: str
    owner: str | None = None


class AIAnalysis(BaseModel):
    summary: str
    key_points: list[str] = Field(..., max_length=10)
    action_items: list[ActionItem] = Field(default_factory=list)
    sentiment: SentimentType


class LLMUsage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class LLMResponse(BaseModel):
    analysis: AIAnalysis
    usage: LLMUsage
    provider: str
    model: str
