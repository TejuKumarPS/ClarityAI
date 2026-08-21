from abc import ABC, abstractmethod
from app.llm.models import AIAnalysis


class LLMProvider(ABC):
    @abstractmethod
    def analyze(self, transcript: str) -> AIAnalysis:
        """Analyze a transcript and return structured AIAnalysis."""
        pass
