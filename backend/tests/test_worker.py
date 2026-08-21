import uuid
import time
from datetime import datetime, timezone
import pytest
import redis
from celery.exceptions import MaxRetriesExceededError, Retry

from app.core.config import settings
from app.models.job import Job
from app.models.user import User
from app.llm.fake_provider import FakeLLMProvider
from app.llm.exceptions import LLMInputTooLargeError
from app.processing import (
    ProcessingStage,
    ProcessingContext,
    ProcessingPipeline,
    ProcessingError,
    create_default_pipeline,
)
from app.worker.celery_app import celery_app
from app.worker.tasks import process_job
import app.worker.tasks as tasks_module


# ==========================================
# Redis Connectivity Tests
# ==========================================

def test_redis_connectivity():
    r = redis.from_url(settings.REDIS_URL)
    assert r.ping() is True


def test_celery_broker_connection():
    conn = celery_app.connection()
    conn.connect()
    assert conn.connected is True
    conn.close()


# ==========================================
# Celery Task Integration Tests
# ==========================================

def test_process_job_successful_lifecycle(db, monkeypatch):
    fake_provider = FakeLLMProvider()
    test_pipeline = create_default_pipeline(llm_provider=fake_provider)
    monkeypatch.setattr(tasks_module, "_pipeline_override", test_pipeline)

    user = User(
        email=f"worker_test_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="mockhash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Sprint retrospective discussion notes.",
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id_str = str(job.id)

    # Execute task synchronously
    result = process_job.apply(args=[job_id_str]).get()

    db.expire_all()
    updated_job = db.query(Job).filter(Job.id == job.id).first()
    assert updated_job.status == "complete"
    assert updated_job.result["processor"] == "clarityai-pipeline"
    assert updated_job.result["version"] == "0.3.0"
    assert updated_job.result["job_id"] == job_id_str
    assert updated_job.result["metadata"]["word_count"] == 4
    assert updated_job.result["ai_analysis"] is not None
    assert updated_job.result["ai_analysis"]["sentiment"] == "positive"
    assert len(updated_job.result["ai_analysis"]["action_items"]) == 2

    # Observability columns verification
    assert updated_job.processing_started_at is not None
    assert updated_job.completed_at is not None
    assert isinstance(updated_job.processing_duration_ms, int)
    assert updated_job.processing_duration_ms >= 0
    assert updated_job.llm_provider == "fake"
    assert updated_job.llm_model == "fake-model"
    assert updated_job.llm_input_tokens == 100
    assert updated_job.llm_output_tokens == 50
    assert updated_job.llm_total_tokens == 150
    assert updated_job.error_code is None
    assert updated_job.retry_count == 0

    # DB observability fields match ProcessingResult LLM metadata
    assert updated_job.llm_input_tokens == updated_job.result["llm_usage"]["input_tokens"]
    assert updated_job.llm_output_tokens == updated_job.result["llm_usage"]["output_tokens"]
    assert updated_job.llm_total_tokens == updated_job.result["llm_usage"]["total_tokens"]
    assert updated_job.llm_provider == updated_job.result["llm_provider"]
    assert updated_job.llm_model == updated_job.result["llm_model"]

    assert result == updated_job.result
    assert db.query(Job).filter(Job.id == job.id).count() == 1


def test_process_job_idempotency_duplicate_execution(db, monkeypatch):
    fake_provider = FakeLLMProvider()
    test_pipeline = create_default_pipeline(llm_provider=fake_provider)
    monkeypatch.setattr(tasks_module, "_pipeline_override", test_pipeline)

    user = User(
        email=f"idempotent_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="mockhash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Important executive decisions.",
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # First execution
    res1 = process_job.apply(args=[str(job.id)]).get()
    assert fake_provider.call_count == 1

    db.expire_all()
    completed_job = db.query(Job).filter(Job.id == job.id).first()
    original_completed_at = completed_job.completed_at
    original_started_at = completed_job.processing_started_at
    original_duration_ms = completed_job.processing_duration_ms
    original_tokens = completed_job.llm_total_tokens

    # Second execution (duplicate message)
    res2 = process_job.apply(args=[str(job.id)]).get()

    # Provider must NOT have been called again
    assert fake_provider.call_count == 1

    db.expire_all()
    rechecked_job = db.query(Job).filter(Job.id == job.id).first()
    assert rechecked_job.status == "complete"
    assert rechecked_job.completed_at == original_completed_at
    assert rechecked_job.processing_started_at == original_started_at
    assert rechecked_job.processing_duration_ms == original_duration_ms
    assert rechecked_job.llm_total_tokens == original_tokens
    assert res1 == res2
    assert db.query(Job).filter(Job.id == job.id).count() == 1


def test_process_job_transient_failure_and_retry(db, monkeypatch):
    user = User(
        email=f"retry_user_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="mockhash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Testing transient network glitch during processing.",
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    attempts = {"count": 0}

    class FlakyStage(ProcessingStage):
        @property
        def name(self) -> str:
            return "flaky"

        def process(self, context: ProcessingContext) -> ProcessingContext:
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise ConnectionError("Temporary connection timeout")
            return context

    flaky_pipeline = ProcessingPipeline(stages=[FlakyStage()])
    monkeypatch.setattr(tasks_module, "_pipeline_override", flaky_pipeline)

    # Attempt 1: raises Retry
    with pytest.raises(Retry):
        process_job.apply(args=[str(job.id)], throw=True)

    db.expire_all()
    retried_job = db.query(Job).filter(Job.id == job.id).first()
    assert retried_job.retry_count == 1
    assert retried_job.status == "processing"
    # Retry attempt must NOT persist terminal duration
    assert retried_job.processing_duration_ms is None
    first_attempt_start = retried_job.processing_started_at
    assert first_attempt_start is not None

    time.sleep(0.01)

    # Attempt 2: succeeds
    process_job.apply(args=[str(job.id)], retries=1, throw=True)

    db.expire_all()
    final_job = db.query(Job).filter(Job.id == job.id).first()
    assert final_job.status == "complete"
    assert final_job.result["processor"] == "clarityai-pipeline"
    # Final retry persists terminal duration
    assert final_job.processing_duration_ms is not None
    assert final_job.processing_duration_ms >= 0
    # Next retry replaced processing_started_at with its own start time
    assert final_job.processing_started_at >= first_attempt_start


def test_process_job_permanent_failure_exhausted_retries(db, monkeypatch):
    user = User(
        email=f"fail_user_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="mockhash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Testing permanently broken processing pipeline.",
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    class BrokenStage(ProcessingStage):
        @property
        def name(self) -> str:
            return "broken"

        def process(self, context: ProcessingContext) -> ProcessingContext:
            raise ProcessingError("Unrecoverable internal failure")

    broken_pipeline = ProcessingPipeline(stages=[BrokenStage()])
    monkeypatch.setattr(tasks_module, "_pipeline_override", broken_pipeline)

    # Exhaust retries: max_retries = 3
    with pytest.raises(MaxRetriesExceededError):
        process_job.apply(args=[str(job.id)], retries=settings.CELERY_TASK_MAX_RETRIES, throw=True)

    db.expire_all()
    failed_job = db.query(Job).filter(Job.id == job.id).first()
    assert failed_job.status == "failed"
    assert failed_job.error_code == "PROCESSING_ERROR"
    assert failed_job.result == {
        "error": {
            "code": "PROCESSING_ERROR",
            "message": "An unexpected error occurred during job processing",
        }
    }
    assert failed_job.retry_count == settings.CELERY_TASK_MAX_RETRIES
    assert isinstance(failed_job.processing_duration_ms, int)
    assert failed_job.processing_duration_ms >= 0


def test_process_job_non_retryable_error_fails_immediately(db, monkeypatch):
    user = User(
        email=f"nonretry_user_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="mockhash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Oversized transcript text.",
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    class OversizedStage(ProcessingStage):
        @property
        def name(self) -> str:
            return "oversized"

        def process(self, context: ProcessingContext) -> ProcessingContext:
            raise LLMInputTooLargeError("Transcript exceeds maximum allowed characters")

    pipeline = ProcessingPipeline(stages=[OversizedStage()])
    monkeypatch.setattr(tasks_module, "_pipeline_override", pipeline)

    with pytest.raises(LLMInputTooLargeError):
        process_job.apply(args=[str(job.id)], throw=True)

    db.expire_all()
    failed_job = db.query(Job).filter(Job.id == job.id).first()
    assert failed_job.status == "failed"
    assert failed_job.error_code == "LLM_INPUT_TOO_LARGE"
    assert failed_job.result == {
        "error": {
            "code": "LLM_INPUT_TOO_LARGE",
            "message": "Transcript exceeds maximum allowed input size",
        }
    }
    assert failed_job.retry_count == 0  # Not retried
    assert isinstance(failed_job.processing_duration_ms, int)
    assert failed_job.processing_duration_ms >= 0


def test_process_job_nonexistent_job_id():
    fake_id = str(uuid.uuid4())
    result = process_job.apply(args=[fake_id]).get()
    assert result is None


def test_process_job_invalid_uuid_string():
    result = process_job.apply(args=["not-a-valid-uuid"]).get()
    assert result is None


# ==========================================
# Enqueue Failure Handling Tests
# ==========================================

@pytest.mark.anyio
async def test_job_creation_enqueue_failure_handling(client, db, monkeypatch):
    from tests.test_jobs import register_and_get_token

    token = await register_and_get_token(client, email="enqueue_fail@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    def mock_delay_fail(job_id):
        raise redis.ConnectionError("Redis connection refused")

    monkeypatch.setattr("app.worker.tasks.process_job.delay", mock_delay_fail)

    payload = {
        "input_type": "text_paste",
        "content": "Valid meeting transcript that fails to enqueue.",
    }
    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 500
    assert "failed to enqueue" in response.json()["detail"]

    # Verify job remains committed in PostgreSQL as pending
    user = db.query(User).filter(User.email == "enqueue_fail@example.com").first()
    job = db.query(Job).filter(Job.user_id == user.id).first()
    assert job is not None
    assert job.status == "pending"
