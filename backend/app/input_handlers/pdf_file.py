import io
from typing import Optional, Union
from pypdf import PdfReader
from pypdf.errors import PdfReadError, EmptyFileError

from app.input_handlers.base import InputHandler
from app.input_handlers.exceptions import (
    EmptyTranscriptError,
    InvalidFileFormatError,
    TranscriptExtractionError,
)


class PdfFileHandler(InputHandler):
    def extract_text(
        self,
        content: Union[str, bytes],
        filename: Optional[str] = None,
    ) -> str:
        if content is None:
            raise EmptyTranscriptError("File content cannot be empty")

        if filename and not filename.lower().endswith(".pdf"):
            raise InvalidFileFormatError(f"Invalid file extension: expected a .pdf file, got '{filename}'")

        if isinstance(content, bytes):
            data = content
        elif isinstance(content, str):
            data = content.encode("utf-8")
        else:
            raise InvalidFileFormatError("Expected bytes or string for .pdf file content")

        if len(data) == 0:
            raise EmptyTranscriptError("PDF file is empty (0 bytes)")

        self.validate_file_size(data)

        try:
            stream = io.BytesIO(data)
            reader = PdfReader(stream)
            if len(reader.pages) == 0:
                raise EmptyTranscriptError("PDF document contains no pages")

            extracted_pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text and text.strip():
                    extracted_pages.append(text.strip())

        except (PdfReadError, EmptyFileError) as exc:
            raise InvalidFileFormatError(f"Failed to read PDF document: {exc}") from exc
        except (EmptyTranscriptError, InvalidFileFormatError):
            raise
        except Exception as exc:
            raise TranscriptExtractionError(f"Unexpected error while extracting PDF text: {exc}") from exc

        if not extracted_pages:
            raise TranscriptExtractionError(
                "No extractable text found in PDF document. Scanned or image-only PDFs are not supported."
            )

        combined_text = "\n\n".join(extracted_pages)
        normalized = self.normalize_text(combined_text)
        self.validate_transcript_text(normalized)
        return normalized
