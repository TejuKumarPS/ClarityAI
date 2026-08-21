from app.llm.base import LLMProvider
from app.llm.models import AIAnalysis, ActionItem


class FakeLLMProvider(LLMProvider):
    def __init__(self, fixed_analysis: AIAnalysis | None = None):
        self.fixed_analysis = fixed_analysis or AIAnalysis(
            summary="Meeting discussion focused on quarterly roadmap deliverables and infrastructure scalability.",
            key_points=[
                "Infrastructure scalability goals approved for Q4.",
                "Engineering team aligned on release timelines.",
            ],
            action_items=[
                ActionItem(task="Deploy staging cluster", owner="Rahul"),
                ActionItem(task="Review architecture documentation", owner=None),
            ],
            sentiment="positive",
        )

    def analyze(self, transcript: str) -> AIAnalysis:
        return self.fixed_analysis
