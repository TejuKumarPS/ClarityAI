import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable
from celery.exceptions import MaxRetriesExceededError

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.job import Job
from app.processing import ProcessingContext, ProcessingPipeline, create_default_pipeline
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

default_pipeline: ProcessingPipeline = create_default_pipeline()
_pipeline_override: Optional[ProcessingPipeline] = None


@celery_app.task(
    bind=True,
    max_retries=settings.CELERY_TASK_MAX_RETRIES,
    default_retry_delay=settings.CELERY_TASK_RETRY_BACKOFF,
    name="process_job",
)
def process_job(self, job_id: str) -> Optional[Dict[str, Any]]:
    logger.info(f"Task received: job_id={job_id}")
    db = SessionLocal()

    try:
        try:
            job_uuid = uuid.UUID(job_id)
        except (ValueError, TypeError) as exc:
            logger.error(f"Invalid job_id format: {job_id} ({exc})")
            return None

        job = db.query(Job).filter(Job.id == job_uuid).first()
        if not job:
            logger.error(f"Job not found in database: {job_id}")
            return None

        if job.status == "complete":
            logger.info(f"Job {job_id} is already complete. Skipping duplicate execution.")
            return job.result

        job.status = "processing"
        db.commit()
        db.refresh(job)
        logger.info(f"Job processing started: job_id={job_id}")

        context = ProcessingContext(
            job_id=str(job.id),
            transcript=job.raw_transcript or "",
        )
        pipeline = _pipeline_override or default_pipeline
        processing_result = pipeline.process(context)
        result_data = processing_result.model_dump()

        job.status = "complete"
        job.result = result_data
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        logger.info(f"Job completed successfully: job_id={job_id}")
        return job.result


    except Exception as exc:
        logger.warning(f"Error processing job {job_id}: {exc}")
        retries_so_far = self.request.retries
        next_retry_count = retries_so_far + 1

        if retries_so_far >= self.max_retries:
            logger.error(f"Max retries ({self.max_retries}) exceeded for job {job_id}. Marking as failed.")
            try:
                job = db.query(Job).filter(Job.id == job_uuid).first()
                if job:
                    job.status = "failed"
                    job.retry_count = retries_so_far
                    job.result = {"error": f"Processing failed after maximum retries exceeded: {exc}"}
                    db.commit()
            except Exception as final_exc:
                logger.error(f"Failed to set status=failed for job {job_id}: {final_exc}")
            raise MaxRetriesExceededError(f"Job {job_id} failed after {self.max_retries} retries: {exc}") from exc

        try:
            job = db.query(Job).filter(Job.id == job_uuid).first()
            if job and job.status != "complete":
                job.retry_count = next_retry_count
                db.commit()
        except Exception as db_exc:
            logger.error(f"Failed to update retry_count for job {job_id}: {db_exc}")

        logger.info(f"Retrying job {job_id} (attempt {next_retry_count}/{self.max_retries})")
        raise self.retry(exc=exc)


    finally:
        db.close()
