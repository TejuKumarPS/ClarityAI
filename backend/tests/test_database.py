import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.models.job import Job


def test_database_connection(db):
    result = db.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_user_creation_and_fields(db):
    user = User(
        email="testuser@example.com",
        password_hash="mock_hashed_password_123",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert isinstance(user.id, uuid.UUID)
    assert user.email == "testuser@example.com"
    assert user.password_hash == "mock_hashed_password_123"
    assert user.created_at is not None


def test_user_email_unique_constraint(db):
    user1 = User(
        email="duplicate@example.com",
        password_hash="hash1",
    )
    db.add(user1)
    db.commit()

    user2 = User(
        email="duplicate@example.com",
        password_hash="hash2",
    )
    db.add(user2)
    with pytest.raises(IntegrityError):
        db.commit()


def test_job_creation_and_defaults(db):
    user = User(
        email="jobcreator@example.com",
        password_hash="hash_creator",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Meeting transcript content discussing Q3 goals.",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    assert isinstance(job.id, uuid.UUID)
    assert job.user_id == user.id
    assert job.input_type == "text_paste"
    assert job.raw_transcript == "Meeting transcript content discussing Q3 goals."
    assert job.status == "pending"
    assert job.retry_count == 0
    assert job.result is None
    assert job.completed_at is None
    assert job.created_at is not None


def test_job_foreign_key_constraint(db):
    non_existent_user_id = uuid.uuid4()
    job = Job(
        user_id=non_existent_user_id,
        input_type="txt_file",
        raw_transcript="Some orphan transcript.",
    )
    db.add(job)
    with pytest.raises(IntegrityError):
        db.commit()


def test_job_jsonb_result_storage(db):
    user = User(
        email="jsonb_test@example.com",
        password_hash="hash_jsonb",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    mock_intelligence_result = {
        "meeting_title": "Sprint Planning Q3",
        "summary": "Team aligned on sprint goals and task assignments.",
        "action_items": [
            {"task": "Setup database", "owner": "Teju", "deadline": "2026-08-22"}
        ],
        "decisions": ["Approved migration to PostgreSQL 18"],
        "participants": ["Teju", "Alex"],
    }

    job = Job(
        user_id=user.id,
        input_type="pdf_file",
        raw_transcript="Sprint transcript",
        status="complete",
        result=mock_intelligence_result,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    assert job.result is not None
    assert job.result["meeting_title"] == "Sprint Planning Q3"
    assert len(job.result["action_items"]) == 1
    assert job.result["action_items"][0]["owner"] == "Teju"
    assert job.result["decisions"] == ["Approved migration to PostgreSQL 18"]


def test_user_job_relationship(db):
    user = User(
        email="relation_test@example.com",
        password_hash="hash_rel",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job1 = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Transcript 1",
    )
    job2 = Job(
        user_id=user.id,
        input_type="txt_file",
        raw_transcript="Transcript 2",
    )
    db.add_all([job1, job2])
    db.commit()
    db.refresh(user)

    assert len(user.jobs) == 2
    assert job1.user.email == "relation_test@example.com"
    assert job2.user.email == "relation_test@example.com"


def test_user_deletion_restricted_no_cascade(db):
    user = User(
        email="nocascade@example.com",
        password_hash="hash_nocascade",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Do not delete cascade test transcript.",
    )
    db.add(job)
    db.commit()

    db.delete(user)
    with pytest.raises(IntegrityError):
        db.commit()

