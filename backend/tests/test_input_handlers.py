import io
import pytest
from pypdf import PdfWriter

from app.core.config import settings
from app.input_handlers.base import InputHandler
from app.input_handlers.text import TextPasteHandler
from app.input_handlers.txt_file import TxtFileHandler
from app.input_handlers.pdf_file import PdfFileHandler
from app.input_handlers.factory import InputHandlerFactory
from app.input_handlers.exceptions import (
    TranscriptInputError,
    UnsupportedInputTypeError,
    EmptyTranscriptError,
    TranscriptTooShortError,
    InvalidFileFormatError,
    TranscriptExtractionError,
    FileSizeLimitExceededError,
)


def create_deterministic_pdf(pages_text: list[str]) -> bytes:
    num_pages = len(pages_text)
    font_id = 3
    page_ids = [4 + 2 * i for i in range(num_pages)]
    content_ids = [5 + 2 * i for i in range(num_pages)]

    catalog = "<< /Type /Catalog /Pages 2 0 R >>"
    kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)
    pages_obj = f"<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>"
    font_obj = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    body_parts = [
        "1 0 obj\n" + catalog + "\nendobj\n",
        "2 0 obj\n" + pages_obj + "\nendobj\n",
        f"{font_id} 0 obj\n" + font_obj + "\nendobj\n",
    ]

    for i, text in enumerate(pages_text):
        pid = page_ids[i]
        cid = content_ids[i]
        stream_content = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET"
        page_obj = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {cid} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        content_obj = f"<< /Length {len(stream_content)} >>\nstream\n{stream_content}\nendstream"
        body_parts.append(f"{pid} 0 obj\n{page_obj}\nendobj\n")
        body_parts.append(f"{cid} 0 obj\n{content_obj}\nendobj\n")

    header = "%PDF-1.4\n"
    offsets = [0]
    current_offset = len(header)

    for part in body_parts:
        offsets.append(current_offset)
        current_offset += len(part.encode("latin-1"))

    xref_start = current_offset
    total_objects = 3 + 2 * num_pages + 1
    xref = f"xref\n0 {total_objects}\n0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n"

    trailer = f"trailer\n<< /Size {total_objects} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF"
    full_pdf = header + "".join(body_parts) + xref + trailer
    return full_pdf.encode("latin-1")


# ==========================================
# TextPasteHandler Tests
# ==========================================

def test_text_paste_valid():
    handler = TextPasteHandler()
    raw = "  This is a valid meeting transcript discussing sprint backlog.  "
    result = handler.extract_text(raw)
    assert result == "This is a valid meeting transcript discussing sprint backlog."


def test_text_paste_bytes():
    handler = TextPasteHandler()
    raw = b"Engineering sync transcript covering release timelines and QA."
    result = handler.extract_text(raw)
    assert result == "Engineering sync transcript covering release timelines and QA."


def test_text_paste_whitespace_normalization():
    handler = TextPasteHandler()
    raw = "\r\n  Line 1: Meeting started.\r\nLine 2: Action items assigned.  \r\n"
    result = handler.extract_text(raw)
    assert result == "Line 1: Meeting started.\nLine 2: Action items assigned."


def test_text_paste_empty():
    handler = TextPasteHandler()
    with pytest.raises(EmptyTranscriptError):
        handler.extract_text("")


def test_text_paste_whitespace_only():
    handler = TextPasteHandler()
    with pytest.raises(EmptyTranscriptError):
        handler.extract_text("   \n\t  \r\n   ")


def test_text_paste_too_short():
    handler = TextPasteHandler()
    with pytest.raises(TranscriptTooShortError):
        handler.extract_text("Short")


def test_text_paste_none_input():
    handler = TextPasteHandler()
    with pytest.raises(EmptyTranscriptError):
        handler.extract_text(None)


def test_text_paste_invalid_type():
    handler = TextPasteHandler()
    with pytest.raises(InvalidFileFormatError):
        handler.extract_text(12345)


def test_text_paste_invalid_utf8_bytes():
    handler = TextPasteHandler()
    with pytest.raises(InvalidFileFormatError):
        handler.extract_text(b"\xff\xfe\x80\x81")


# ==========================================
# TxtFileHandler Tests
# ==========================================

def test_txt_file_valid_utf8():
    handler = TxtFileHandler()
    data = "Quarterly Business Review notes with leadership team.".encode("utf-8")
    result = handler.extract_text(data, filename="notes.txt")
    assert result == "Quarterly Business Review notes with leadership team."


def test_txt_file_case_insensitive_extension():
    handler = TxtFileHandler()
    data = "Transcript content with uppercase extension.".encode("utf-8")
    result = handler.extract_text(data, filename="MEETING_TRANSCRIPT.TXT")
    assert result == "Transcript content with uppercase extension."


def test_txt_file_invalid_extension():
    handler = TxtFileHandler()
    data = "Transcript content.".encode("utf-8")
    with pytest.raises(InvalidFileFormatError) as exc_info:
        handler.extract_text(data, filename="meeting.docx")
    assert "Invalid file extension" in str(exc_info.value)


def test_txt_file_empty():
    handler = TxtFileHandler()
    with pytest.raises(EmptyTranscriptError):
        handler.extract_text(b"", filename="empty.txt")


def test_txt_file_whitespace_only():
    handler = TxtFileHandler()
    with pytest.raises(EmptyTranscriptError):
        handler.extract_text(b"   \r\n  \t  ", filename="blank.txt")


def test_txt_file_too_short():
    handler = TxtFileHandler()
    with pytest.raises(TranscriptTooShortError):
        handler.extract_text(b"Tiny", filename="short.txt")


def test_txt_file_invalid_utf8():
    handler = TxtFileHandler()
    invalid_bytes = b"\x80\x81\x82\xff"
    with pytest.raises(InvalidFileFormatError) as exc_info:
        handler.extract_text(invalid_bytes, filename="corrupted.txt")
    assert "could not be decoded as UTF-8" in str(exc_info.value)


def test_txt_file_size_limit_exceeded(monkeypatch):
    handler = TxtFileHandler()
    monkeypatch.setattr(settings, "MAX_INPUT_FILE_SIZE_BYTES", 50)
    oversized_data = b"A" * 100
    with pytest.raises(FileSizeLimitExceededError):
        handler.extract_text(oversized_data, filename="large.txt")


# ==========================================
# PdfFileHandler Tests
# ==========================================

def test_pdf_file_valid_single_page():
    handler = PdfFileHandler()
    pdf_bytes = create_deterministic_pdf(["Sprint Planning: Frontend and Backend roadmap."])
    result = handler.extract_text(pdf_bytes, filename="sprint.pdf")
    assert "Sprint Planning: Frontend and Backend roadmap." in result


def test_pdf_file_valid_multi_page():
    handler = PdfFileHandler()
    pdf_bytes = create_deterministic_pdf([
        "Page 1: Project overview and stakeholder alignment.",
        "Page 2: Key deliverables and risk mitigation steps.",
    ])
    result = handler.extract_text(pdf_bytes, filename="meeting.pdf")
    assert "Page 1: Project overview and stakeholder alignment." in result
    assert "Page 2: Key deliverables and risk mitigation steps." in result


def test_pdf_file_case_insensitive_extension():
    handler = PdfFileHandler()
    pdf_bytes = create_deterministic_pdf(["Valid meeting transcript content."])
    result = handler.extract_text(pdf_bytes, filename="REPORT.PDF")
    assert "Valid meeting transcript content." in result


def test_pdf_file_invalid_extension():
    handler = PdfFileHandler()
    pdf_bytes = create_deterministic_pdf(["Some transcript text."])
    with pytest.raises(InvalidFileFormatError) as exc_info:
        handler.extract_text(pdf_bytes, filename="report.csv")
    assert "Invalid file extension" in str(exc_info.value)


def test_pdf_file_empty_bytes():
    handler = PdfFileHandler()
    with pytest.raises(EmptyTranscriptError):
        handler.extract_text(b"", filename="empty.pdf")


def test_pdf_file_no_extractable_text():
    handler = PdfFileHandler()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    stream = io.BytesIO()
    writer.write(stream)
    blank_pdf = stream.getvalue()

    with pytest.raises(TranscriptExtractionError) as exc_info:
        handler.extract_text(blank_pdf, filename="scanned.pdf")
    assert "No extractable text found" in str(exc_info.value)


def test_pdf_file_malformed():
    handler = PdfFileHandler()
    corrupted = b"%PDF-1.4 corrupted header and missing body"
    with pytest.raises(InvalidFileFormatError):
        handler.extract_text(corrupted, filename="corrupt.pdf")


def test_pdf_file_size_limit_exceeded(monkeypatch):
    handler = PdfFileHandler()
    monkeypatch.setattr(settings, "MAX_INPUT_FILE_SIZE_BYTES", 50)
    pdf_bytes = create_deterministic_pdf(["Valid text inside PDF."])
    with pytest.raises(FileSizeLimitExceededError):
        handler.extract_text(pdf_bytes, filename="large.pdf")


# ==========================================
# InputHandlerFactory Tests
# ==========================================

def test_factory_supported_types():
    assert isinstance(InputHandlerFactory.get_handler("text_paste"), TextPasteHandler)
    assert isinstance(InputHandlerFactory.get_handler("txt_file"), TxtFileHandler)
    assert isinstance(InputHandlerFactory.get_handler("pdf_file"), PdfFileHandler)


def test_factory_case_insensitive():
    assert isinstance(InputHandlerFactory.get_handler("TEXT_PASTE"), TextPasteHandler)
    assert isinstance(InputHandlerFactory.get_handler("Txt_File"), TxtFileHandler)
    assert isinstance(InputHandlerFactory.get_handler("PDF_FILE"), PdfFileHandler)


def test_factory_unsupported_type():
    with pytest.raises(UnsupportedInputTypeError) as exc_info:
        InputHandlerFactory.get_handler("audio_file")
    assert "Unsupported input type 'audio_file'" in str(exc_info.value)


def test_factory_invalid_input_type():
    with pytest.raises(UnsupportedInputTypeError):
        InputHandlerFactory.get_handler("")
    with pytest.raises(UnsupportedInputTypeError):
        InputHandlerFactory.get_handler(None)


def test_factory_custom_handler_registration():
    class MockCustomHandler(InputHandler):
        def extract_text(self, content, filename=None):
            return "Custom handler processed transcript."

    InputHandlerFactory.register_handler("custom_format", MockCustomHandler)
    handler = InputHandlerFactory.get_handler("custom_format")
    assert isinstance(handler, MockCustomHandler)
    assert handler.extract_text("raw data") == "Custom handler processed transcript."


def test_factory_register_invalid_handler():
    class NotAHandler:
        pass

    with pytest.raises(TypeError):
        InputHandlerFactory.register_handler("invalid_cls", NotAHandler)


def test_factory_register_invalid_type_name():
    class ValidSubclass(InputHandler):
        def extract_text(self, content, filename=None):
            return "text"

    with pytest.raises(ValueError):
        InputHandlerFactory.register_handler("", ValidSubclass)


def test_factory_extract_helper():
    text = "Team retrospective transcript covering key achievements."
    result = InputHandlerFactory.extract("text_paste", text)
    assert result == text
