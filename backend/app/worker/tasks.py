import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from celery.exceptions import MaxRetriesExceededError

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.job import Job
from app.processing import ProcessingContext, ProcessingPipeline, create_default_pipeline
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMInputTooLargeError,
    LLMResponseValidationError,
    LLMProviderError,
)
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

default_pipeline: ProcessingPipeline = create_default_pipeline()
_pipeline_override: Optional[ProcessingPipeline] = None


def _get_error_details(exc: Exception) -> Tuple[str, str, bool]:
    """Map exception to (error_code, safe_message, is_non_retryable)."""
    if isinstance(exc, LLMConfigurationError):
        return "LLM_CONFIGURATION_ERROR", "LLM service is improperly configured", True
    if isinstance(exc, LLMInputTooLargeError):
        return "LLM_INPUT_TOO_LARGE", "Transcript exceeds maximum allowed input size", True
    if isinstance(exc, LLMResponseValidationError):
        return "LLM_RESPONSE_INVALID", "LLM provider returned an invalid structured response", True
    if isinstance(exc, LLMProviderError):
        return "LLM_PROVIDER_ERROR", "LLM provider temporarily unavailable or encountered a transient error", False
    return "PROCESSING_ERROR", "An unexpected error occurred during job processing", False


@celery_app.task(
    bind=True,
    max_retries=settings.CELERY_TASK_MAX_RETRIES,
    default_retry_delay=settings.CELERY_TASK_RETRY_BACKOFF,
    name="process_job",
)
def process_job(self, job_id: str) -> Optional[Dict[str, Any]]:
    start_mono = time.monotonic()
    db = SessionLocal()

    try:
        try:
            job_uuid = uuid.UUID(job_id)
        except (ValueError, TypeError) as exc:
            logger.error("job_processing_invalid_uuid: job_id=%s error=%s", job_id, exc)
            return None

        job = db.query(Job).filter(Job.id == job_uuid).first()
        if not job:
            logger.error("job_processing_not_found: job_id=%s", job_id)
            return None

        if job.status == "complete":
            logger.info("job_processing_duplicate_skipped: job_id=%s", job_id)
            return job.result

        # Initialize attempt state
        job.status = "processing"
        job.processing_started_at = datetime.now(timezone.utc)
        job.processing_duration_ms = None
        job.error_code = None
        db.commit()
        db.refresh(job)

        attempt_num = self.request.retries + 1
        logger.info("job_processing_started: job_id=%s attempt=%d", job_id, attempt_num)

        context = ProcessingContext(
            job_id=str(job.id),
            transcript=job.raw_transcript or "",
        )
        pipeline = _pipeline_override or default_pipeline
        processing_result = pipeline.process(context)
        result_data = processing_result.model_dump()

        elapsed_ms = int((time.monotonic() - start_mono) * 1000)

        # Successful completion state
        job.status = "complete"
        job.result = result_data
        job.completed_at = datetime.now(timezone.utc)
        job.processing_duration_ms = elapsed_ms
        job.error_code = None

        if processing_result.llm_provider:
            job.llm_provider = processing_result.llm_provider
            job.llm_model = processing_result.llm_model

        if processing_result.llm_usage:
            job.llm_input_tokens = processing_result.llm_usage.input_tokens
            job.llm_output_tokens = processing_result.llm_usage.output_tokens
            job.llm_total_tokens = processing_result.llm_usage.total_tokens

        db.commit()
        db.refresh(job)

        logger.info(
            "job_processing_completed: job_id=%s duration_ms=%d provider=%s model=%s total_tokens=%d",
            job_id,
            elapsed_ms,
            job.llm_provider or "none",
            job.llm_model or "none",
            job.llm_total_tokens or 0,
        )
        return job.result

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start_mono) * 1000)
        retries_so_far = self.request.retries
        next_retry_count = retries_so_far + 1
        error_code, safe_message, is_non_retryable = _get_error_details(exc)

        if retries_so_far >= self.max_retries or is_non_retryable:
            reason = "non-retryable error" if is_non_retryable else f"max retries ({self.max_retries}) exceeded"
            logger.error(
                "job_processing_failed: job_id=%s error_code=%s retry_count=%d duration_ms=%d reason=%s",
                job_id,
                error_code,
                retries_so_far,
                elapsed_ms,
                reason,
            )
            try:
                job = db.query(Job).filter(Job.id == job_uuid).first()
                if job:
                    job.status = "failed"
                    job.retry_count = retries_so_far
                    job.processing_duration_ms = elapsed_ms
                    job.error_code = error_code
                    job.result = {
                        "error": {
                            "code": error_code,
                            "message": safe_message,
                        }
                    }
                    db.commit()
            except Exception as final_exc:
                logger.error("job_processing_failed_db_error: job_id=%s error=%s", job_id, final_exc)

            if is_non_retryable:
                raise
            raise MaxRetriesExceededError(f"Job {job_id} failed after {self.max_retries} retries: {exc}") from exc

        try:
            job = db.query(Job).filter(Job.id == job_uuid).first()
            if job and job.status != "complete":
                job.retry_count = next_retry_count
                job.processing_duration_ms = None
                job.error_code = None
                db.commit()
        except Exception as db_exc:
            logger.error("job_processing_retry_db_error: job_id=%s error=%s", job_id, db_exc)

        logger.info(
            "job_processing_retry: job_id=%s error_code=%s next_attempt=%d/%d",
            job_id,
            error_code,
            next_retry_count,
            self.max_retries,
        )
        raise self.retry(exc=exc)

    finally:
        db.close()
