from app.llm.base import LLMProvider
from app.llm.models import (
    AIAnalysis,
    Decision,
    ActionItem,
    Risk,
    OpenQuestion,
    LLMUsage,
    LLMResponse,
)


class FakeLLMProvider(LLMProvider):
    def __init__(
        self,
        fixed_analysis: AIAnalysis | None = None,
        usage: LLMUsage | None = None,
        provider: str = "fake",
        model: str = "fake-model",
    ):
        self.fixed_analysis = fixed_analysis or AIAnalysis(
            summary="Meeting discussion focused on quarterly roadmap deliverables and infrastructure scalability.",
            key_points=[
                "Infrastructure scalability goals approved for Q4.",
                "Engineering team aligned on release timelines.",
            ],
            decisions=[
                Decision(
                    decision="Migrate primary database to PostgreSQL 18",
                    rationale="Enables high availability failover and improved query planner performance",
                )
            ],
            action_items=[
                ActionItem(task="Deploy staging cluster", owner="Rahul"),
                ActionItem(task="Review architecture documentation", owner=None),
            ],
            risks=[
                Risk(
                    description="Replication lag during initial cross-region database sync",
                    severity="medium",
                )
            ],
            open_questions=[
                OpenQuestion(
                    question="What is the rollback procedure if failover testing encounters timeout?",
                    owner="David",
                )
            ],
            sentiment="positive",
        )
        self.usage = usage or LLMUsage(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        self.provider = provider
        self.model = model
        self.call_count: int = 0

    def analyze(self, transcript: str) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(
            analysis=self.fixed_analysis,
            usage=self.usage,
            provider=self.provider,
            model=self.model,
        )
