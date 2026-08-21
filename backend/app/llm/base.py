from abc import ABC, abstractmethod
from app.llm.models import LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    def analyze(self, transcript: str) -> LLMResponse:
        """Analyze a transcript and return structured LLMResponse."""
        pass
