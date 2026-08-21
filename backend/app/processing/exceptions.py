class ProcessingError(Exception):
    """Base exception for document intelligence pipeline processing errors."""
    pass


class InvalidProcessingContextError(ProcessingError):
    """Raised when the processing context is invalid or missing required data."""
    pass


class PipelineExecutionError(ProcessingError):
    """Raised when a pipeline stage fails to execute."""
    pass
