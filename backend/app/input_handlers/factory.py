from typing import Dict, Type, Union, Optional
from app.input_handlers.base import InputHandler
from app.input_handlers.text import TextPasteHandler
from app.input_handlers.txt_file import TxtFileHandler
from app.input_handlers.pdf_file import PdfFileHandler
from app.input_handlers.exceptions import UnsupportedInputTypeError


class InputHandlerFactory:
    _registry: Dict[str, Type[InputHandler]] = {
        "text_paste": TextPasteHandler,
        "txt_file": TxtFileHandler,
        "pdf_file": PdfFileHandler,
    }

    @classmethod
    def register_handler(cls, input_type: str, handler_cls: Type[InputHandler]) -> None:
        if not isinstance(input_type, str) or not input_type.strip():
            raise ValueError("input_type must be a non-empty string")

        if not isinstance(handler_cls, type) or not issubclass(handler_cls, InputHandler):
            raise TypeError(f"handler_cls must be a subclass of InputHandler, got {handler_cls}")

        cls._registry[input_type.strip().lower()] = handler_cls

    @classmethod
    def get_handler(cls, input_type: str) -> InputHandler:
        if not input_type or not isinstance(input_type, str):
            raise UnsupportedInputTypeError(f"Invalid input type: {input_type}")

        normalized_type = input_type.strip().lower()
        handler_cls = cls._registry.get(normalized_type)

        if not handler_cls:
            supported = ", ".join(sorted(cls._registry.keys()))
            raise UnsupportedInputTypeError(
                f"Unsupported input type '{input_type}'. Supported types: {supported}"
            )

        return handler_cls()

    @classmethod
    def extract(
        cls,
        input_type: str,
        content: Union[str, bytes],
        filename: Optional[str] = None,
    ) -> str:
        handler = cls.get_handler(input_type)
        return handler.extract_text(content, filename=filename)
