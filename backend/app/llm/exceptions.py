from app.processing.exceptions import ProcessingError


class LLMError(ProcessingError):
    """Base exception for LLM operations."""
    pass


class LLMConfigurationError(LLMError):
    """Non-retryable: Raised when LLM configuration or authentication is invalid."""
    pass


class LLMInputTooLargeError(LLMError):
    """Non-retryable: Raised when transcript input exceeds the configured character limit."""
    pass


class LLMResponseValidationError(LLMError):
    """Non-retryable: Raised when the LLM response fails validation or cannot be parsed."""
    pass


class LLMProviderError(LLMError):
    """Retryable: Raised on transient provider errors (network, timeout, rate limits, 5xx)."""
    pass
