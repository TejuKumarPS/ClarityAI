import logging
from typing import Any
import openai

from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.models import AIAnalysis
from app.llm.exceptions import (
    LLMError,
    LLMConfigurationError,
    LLMInputTooLargeError,
    LLMResponseValidationError,
    LLMProviderError,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are ClarityAI's document intelligence analyzer. "
    "Analyze the provided transcript and produce a structured analysis strictly grounded in the text. "
    "Do not invent facts, tasks, or owners that are not directly supported by the transcript. "
    "Set the action item owner to null if no responsible individual is explicitly identified. "
    "Sentiment must be exactly one of: positive, neutral, negative, mixed."
)


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_input_chars: int | None = None,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.max_input_chars = max_input_chars or settings.MAX_LLM_INPUT_CHARACTERS
        self._client: Any = None

    def _get_client(self) -> openai.OpenAI:
        if not self.api_key or not self.api_key.strip():
            raise LLMConfigurationError("OPENAI_API_KEY is not configured")
        if self._client is None:
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def analyze(self, transcript: str) -> AIAnalysis:
        if len(transcript) > self.max_input_chars:
            raise LLMInputTooLargeError(
                f"Transcript length ({len(transcript)} chars) exceeds limit ({self.max_input_chars} chars)"
            )

        client = self._get_client()

        try:
            completion = client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Transcript:\n{transcript}"},
                ],
                response_format=AIAnalysis,
            )

            choice = completion.choices[0]
            if getattr(choice.message, "refusal", None):
                raise LLMResponseValidationError(f"Model refused analysis: {choice.message.refusal}")

            parsed = choice.message.parsed
            if not parsed:
                raise LLMResponseValidationError("Model returned empty parsed structured output")

            return parsed

        except openai.AuthenticationError as exc:
            logger.error("OpenAI authentication failed")
            raise LLMConfigurationError(f"OpenAI authentication failed: {exc}") from exc
        except openai.PermissionDeniedError as exc:
            logger.error("OpenAI permission denied")
            raise LLMConfigurationError(f"OpenAI permission denied: {exc}") from exc
        except openai.RateLimitError as exc:
            logger.warning("OpenAI rate limit encountered")
            raise LLMProviderError(f"OpenAI rate limit encountered: {exc}") from exc
        except (openai.APITimeoutError, openai.APIConnectionError) as exc:
            logger.warning(f"OpenAI connectivity error: {exc}")
            raise LLMProviderError(f"OpenAI network/timeout error: {exc}") from exc
        except openai.InternalServerError as exc:
            logger.warning(f"OpenAI 5xx server error: {exc}")
            raise LLMProviderError(f"OpenAI server error: {exc}") from exc
        except openai.LengthFinishReasonError as exc:
            logger.error("OpenAI completion token length exceeded")
            raise LLMResponseValidationError(f"OpenAI response exceeded token limits: {exc}") from exc
        except openai.BadRequestError as exc:
            logger.error(f"OpenAI bad request: {exc}")
            raise LLMResponseValidationError(f"OpenAI invalid request: {exc}") from exc
        except LLMError:
            raise
        except openai.OpenAIError as exc:
            logger.error(f"OpenAI error: {exc}")
            raise LLMProviderError(f"OpenAI processing error: {exc}") from exc
        except Exception as exc:
            logger.error(f"Unexpected error during OpenAI analysis: {exc}")
            raise LLMProviderError(f"Unexpected error in LLM provider: {exc}") from exc

