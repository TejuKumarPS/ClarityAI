from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

SentimentType = Literal["positive", "neutral", "negative", "mixed"]


class Decision(BaseModel):
    decision: str
    rationale: str | None = None

    model_config = ConfigDict(extra="forbid")


class ActionItem(BaseModel):
    task: str
    owner: str | None = None

    model_config = ConfigDict(extra="forbid")


class Risk(BaseModel):
    description: str
    severity: Literal["low", "medium", "high"]

    model_config = ConfigDict(extra="forbid")


class OpenQuestion(BaseModel):
    question: str
    owner: str | None = None

    model_config = ConfigDict(extra="forbid")


class AIAnalysis(BaseModel):
    summary: str
    key_points: list[str] = Field(..., max_length=10)
    decisions: list[Decision] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    sentiment: SentimentType

    model_config = ConfigDict(extra="forbid")


class LLMUsage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class LLMResponse(BaseModel):
    analysis: AIAnalysis
    usage: LLMUsage
    provider: str
    model: str
