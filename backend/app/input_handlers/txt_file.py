from typing import Optional, Union
from app.input_handlers.base import InputHandler
from app.input_handlers.exceptions import (
    EmptyTranscriptError,
    InvalidFileFormatError,
)


class TxtFileHandler(InputHandler):
    def extract_text(
        self,
        content: Union[str, bytes],
        filename: Optional[str] = None,
    ) -> str:
        if content is None:
            raise EmptyTranscriptError("File content cannot be empty")

        if filename and not filename.lower().endswith(".txt"):
            raise InvalidFileFormatError(f"Invalid file extension: expected a .txt file, got '{filename}'")

        if isinstance(content, str):
            data = content.encode("utf-8")
        elif isinstance(content, bytes):
            data = content
        else:
            raise InvalidFileFormatError("Expected string or bytes for .txt file content")

        self.validate_file_size(data)

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidFileFormatError("File content could not be decoded as UTF-8 text") from exc

        normalized = self.normalize_text(text)
        self.validate_transcript_text(normalized)
        return normalized
