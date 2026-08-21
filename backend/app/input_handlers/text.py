from typing import Optional, Union
from app.input_handlers.base import InputHandler
from app.input_handlers.exceptions import (
    EmptyTranscriptError,
    InvalidFileFormatError,
)


class TextPasteHandler(InputHandler):
    def extract_text(
        self,
        content: Union[str, bytes],
        filename: Optional[str] = None,
    ) -> str:
        if content is None:
            raise EmptyTranscriptError("Transcript content cannot be empty")

        if isinstance(content, bytes):
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise InvalidFileFormatError("Text content could not be decoded as UTF-8") from exc
        elif isinstance(content, str):
            text = content
        else:
            raise InvalidFileFormatError("Expected string or bytes for text input")

        normalized = self.normalize_text(text)
        self.validate_transcript_text(normalized)
        return normalized
