from abc import ABC, abstractmethod
from typing import Optional, Union
from app.core.config import settings
from app.input_handlers.exceptions import (
    EmptyTranscriptError,
    TranscriptTooShortError,
    FileSizeLimitExceededError,
)


class InputHandler(ABC):
    @abstractmethod
    def extract_text(
        self,
        content: Union[str, bytes],
        filename: Optional[str] = None,
    ) -> str:
        pass

    def normalize_text(self, text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        return normalized.strip()

    def validate_transcript_text(self, text: str) -> None:
        if not text or not text.strip():
            raise EmptyTranscriptError("Transcript content cannot be empty or whitespace only")

        stripped_len = len(text.strip())
        if stripped_len < settings.MIN_TRANSCRIPT_LENGTH:
            raise TranscriptTooShortError(
                f"Transcript is too short ({stripped_len} characters; minimum {settings.MIN_TRANSCRIPT_LENGTH} required)"
            )

    def validate_file_size(self, data: bytes) -> None:
        if len(data) > settings.MAX_INPUT_FILE_SIZE_BYTES:
            raise FileSizeLimitExceededError(
                f"File size of {len(data)} bytes exceeds maximum allowed limit of {settings.MAX_INPUT_FILE_SIZE_BYTES} bytes"
            )
