from abc import ABC, abstractmethod
from app.processing.models import ProcessingContext


class ProcessingStage(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the processing stage."""
        pass

    @abstractmethod
    def process(self, context: ProcessingContext) -> ProcessingContext:
        """Execute stage processing on context and return updated context."""
        pass
