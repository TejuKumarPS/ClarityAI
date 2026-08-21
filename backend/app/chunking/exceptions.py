from app.processing.exceptions import ProcessingError


class ChunkingError(ProcessingError):
    """Base exception for chunking and context preparation errors."""
    pass


class InvalidChunkConfigurationError(ChunkingError):
    """Raised when chunk size or overlap configuration is invalid."""
    pass


class EmptyDocumentError(ChunkingError):
    """Raised when attempting to chunk empty or whitespace-only documents."""
    pass


class ChunkingExecutionError(ChunkingError):
    """Raised when chunk generation fails during execution."""
    pass
