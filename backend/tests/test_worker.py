import uuid
from datetime import datetime, timezone
import pytest
import redis
from celery.exceptions import MaxRetriesExceededError, Retry

from app.core.config import settings
from app.models.job import Job
from app.models.user import User
from app.processing import (
    ProcessingStage,
    ProcessingContext,
    ProcessingPipeline,
    ProcessingError,
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

def test_process_job_successful_lifecycle(db):
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
    assert updated_job.result == {
        "processor": "clarityai-pipeline",
        "version": "0.1.0",
        "job_id": job_id_str,
        "metadata": {
            "character_count": len("Sprint retrospective discussion notes."),
            "word_count": 4,
            "line_count": 1,
        },
    }
    assert updated_job.completed_at is not None
    assert updated_job.retry_count == 0
    assert result == updated_job.result

    # Verify no duplicate rows
    count = db.query(Job).filter(Job.id == job.id).count()
    assert count == 1


def test_process_job_idempotency_duplicate_execution(db):
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

    db.expire_all()
    completed_job = db.query(Job).filter(Job.id == job.id).first()
    original_completed_at = completed_job.completed_at

    # Second execution (duplicate message)
    res2 = process_job.apply(args=[str(job.id)]).get()

    db.expire_all()
    rechecked_job = db.query(Job).filter(Job.id == job.id).first()
    assert rechecked_job.status == "complete"
    assert rechecked_job.completed_at == original_completed_at
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

    # Attempt 2: succeeds
    process_job.apply(args=[str(job.id)], retries=1, throw=True)

    db.expire_all()
    final_job = db.query(Job).filter(Job.id == job.id).first()
    assert final_job.status == "complete"
    assert final_job.result["processor"] == "clarityai-pipeline"


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
    assert "error" in failed_job.result
    assert failed_job.retry_count == settings.CELERY_TASK_MAX_RETRIES


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
