from app.processing.exceptions import ProcessingError


class RetrievalError(ProcessingError):
    """Base exception for retrieval errors."""
    pass


class InvalidRetrievalQueryError(RetrievalError):
    """Raised when retrieval query is empty, whitespace, or invalid."""
    pass


class InvalidRetrievalConfigurationError(RetrievalError):
    """Raised when retrieval parameters (e.g., max_results) are invalid."""
    pass
