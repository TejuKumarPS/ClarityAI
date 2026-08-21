class TranscriptInputError(Exception):
    pass


class UnsupportedInputTypeError(TranscriptInputError):
    pass


class EmptyTranscriptError(TranscriptInputError):
    pass


class TranscriptTooShortError(TranscriptInputError):
    pass


class InvalidFileFormatError(TranscriptInputError):
    pass


class TranscriptExtractionError(TranscriptInputError):
    pass


class FileSizeLimitExceededError(TranscriptInputError):
    pass
