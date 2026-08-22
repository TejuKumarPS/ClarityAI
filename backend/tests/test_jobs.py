import uuid
from datetime import datetime, timedelta, timezone
import pytest
import jwt
from app.core.config import settings
from app.models.job import Job
from app.models.user import User
from tests.test_input_handlers import create_deterministic_pdf


async def register_and_get_token(client, email="jobtest@example.com", password="Password123!"):
    await client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": email, "password": password},
    )
    login_res = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": email, "password": password},
    )
    return login_res.json()["access_token"]


# ==========================================
# Authentication Tests
# ==========================================

@pytest.mark.anyio
async def test_create_job_unauthenticated(client):
    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "text_paste", "content": "Valid meeting transcript text here."},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_create_job_invalid_token(client):
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "text_paste", "content": "Valid meeting transcript text here."},
        headers=headers,
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_create_job_expired_token(client):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    headers = {"Authorization": f"Bearer {expired_token}"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "text_paste", "content": "Valid meeting transcript text here."},
        headers=headers,
    )
    assert response.status_code == 401


# ==========================================
# Text Paste Submission Tests
# ==========================================

@pytest.mark.anyio
async def test_create_job_text_paste_success(client, db):
    token = await register_and_get_token(client, email="textjob@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "input_type": "text_paste",
        "content": "  Sprint Planning: Discussion on database schema and API design.  ",
    }
    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    job_id = uuid.UUID(data["id"])
    assert data["input_type"] == "text_paste"
    assert data["status"] == "pending"
    assert "created_at" in data

    # Verify PostgreSQL record
    job = db.query(Job).filter(Job.id == job_id).first()
    assert job is not None
    assert job.input_type == "text_paste"
    assert job.raw_transcript == "Sprint Planning: Discussion on database schema and API design."
    assert job.status == "pending"
    assert job.result is None
    assert job.retry_count == 0
    assert job.completed_at is None
    assert job.created_at is not None

    user = db.query(User).filter(User.email == "textjob@example.com").first()
    assert job.user_id == user.id


# ==========================================
# TXT File Submission Tests
# ==========================================

@pytest.mark.anyio
async def test_create_job_txt_file_success(client, db):
    token = await register_and_get_token(client, email="txtjob@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    txt_content = b"All-Hands Meeting notes: Alignment on product vision and milestones."
    files = {"file": ("all_hands.txt", txt_content, "text/plain")}
    data = {"input_type": "txt_file"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        data=data,
        files=files,
        headers=headers,
    )
    assert response.status_code == 201

    job_id = uuid.UUID(response.json()["id"])
    job = db.query(Job).filter(Job.id == job_id).first()
    assert job is not None
    assert job.input_type == "txt_file"
    assert job.raw_transcript == "All-Hands Meeting notes: Alignment on product vision and milestones."
    assert job.status == "pending"
    assert job.result is None
    assert job.retry_count == 0
    assert job.completed_at is None


# ==========================================
# PDF File Submission Tests
# ==========================================

@pytest.mark.anyio
async def test_create_job_pdf_file_success(client, db):
    token = await register_and_get_token(client, email="pdfjob@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = create_deterministic_pdf([
        "Page 1: Executive committee sync.",
        "Page 2: Financial budget approval.",
    ])
    files = {"file": ("exec_meeting.pdf", pdf_bytes, "application/pdf")}
    data = {"input_type": "pdf_file"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        data=data,
        files=files,
        headers=headers,
    )
    assert response.status_code == 201

    job_id = uuid.UUID(response.json()["id"])
    job = db.query(Job).filter(Job.id == job_id).first()
    assert job is not None
    assert job.input_type == "pdf_file"
    assert "Page 1: Executive committee sync." in job.raw_transcript
    assert "Page 2: Financial budget approval." in job.raw_transcript
    assert job.status == "pending"
    assert job.result is None
    assert job.retry_count == 0
    assert job.completed_at is None


# ==========================================
# Invalid Inputs & Error Handling Tests
# ==========================================

@pytest.mark.anyio
async def test_create_job_empty_text(client):
    token = await register_and_get_token(client, email="emptytext@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "text_paste", "content": ""},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_job_whitespace_text(client):
    token = await register_and_get_token(client, email="whitespacetext@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "text_paste", "content": "   \n\t  \r\n  "},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_job_too_short_text(client):
    token = await register_and_get_token(client, email="shorttext@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "text_paste", "content": "Short"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_job_unsupported_input_type(client):
    token = await register_and_get_token(client, email="unsupported@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "audio_stream", "content": "Some audio transcript"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Unsupported input type" in response.json()["detail"]


@pytest.mark.anyio
async def test_create_job_txt_file_missing_file(client):
    token = await register_and_get_token(client, email="nofile@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        data={"input_type": "txt_file"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "File upload" in response.json()["detail"]


@pytest.mark.anyio
async def test_create_job_pdf_file_missing_file(client):
    token = await register_and_get_token(client, email="nopdffile@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        data={"input_type": "pdf_file"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "File upload" in response.json()["detail"]


@pytest.mark.anyio
async def test_create_job_txt_file_invalid_extension(client):
    token = await register_and_get_token(client, email="badext@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("notes.docx", b"Valid transcript content here.", "application/octet-stream")}
    data = {"input_type": "txt_file"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        data=data,
        files=files,
        headers=headers,
    )
    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]


@pytest.mark.anyio
async def test_create_job_pdf_file_malformed(client):
    token = await register_and_get_token(client, email="corruptpdf@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("corrupt.pdf", b"%PDF-1.4 corrupt junk body", "application/pdf")}
    data = {"input_type": "pdf_file"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        data=data,
        files=files,
        headers=headers,
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_create_job_mismatched_text_paste_with_file(client):
    token = await register_and_get_token(client, email="mismatchtext@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("notes.txt", b"Valid text.", "text/plain")}
    data = {"input_type": "text_paste"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        data=data,
        files=files,
        headers=headers,
    )
    assert response.status_code == 400
    assert "JSON" in response.json()["detail"]


@pytest.mark.anyio
async def test_create_job_mismatched_txt_file_in_json(client):
    token = await register_and_get_token(client, email="mismatchjson@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "txt_file", "content": "Text inside JSON"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "multipart/form-data" in response.json()["detail"]


@pytest.mark.anyio
async def test_create_job_oversized_file(client, monkeypatch):
    token = await register_and_get_token(client, email="oversized@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    monkeypatch.setattr(settings, "MAX_INPUT_FILE_SIZE_BYTES", 50)
    files = {"file": ("large.txt", b"A" * 100, "text/plain")}
    data = {"input_type": "txt_file"}

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        data=data,
        files=files,
        headers=headers,
    )
    assert response.status_code == 413


# ==========================================
# Ownership & Isolation Tests
# ==========================================

@pytest.mark.anyio
async def test_create_job_ownership_user_isolation(client, db):
    token_a = await register_and_get_token(client, email="user_a@example.com")
    token_b = await register_and_get_token(client, email="user_b@example.com")

    user_a = db.query(User).filter(User.email == "user_a@example.com").first()
    user_b = db.query(User).filter(User.email == "user_b@example.com").first()

    # User A creates a job
    headers_a = {"Authorization": f"Bearer {token_a}"}
    res_a = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "text_paste", "content": "User A meeting transcript content."},
        headers=headers_a,
    )
    assert res_a.status_code == 201
    job_a_id = uuid.UUID(res_a.json()["id"])

    job_a = db.query(Job).filter(Job.id == job_a_id).first()
    assert job_a.user_id == user_a.id
    assert job_a.user_id != user_b.id


@pytest.mark.anyio
async def test_create_job_client_cannot_override_user_id(client, db):
    token_a = await register_and_get_token(client, email="legit_user@example.com")
    token_b = await register_and_get_token(client, email="victim_user@example.com")

    legit_user = db.query(User).filter(User.email == "legit_user@example.com").first()
    victim_user = db.query(User).filter(User.email == "victim_user@example.com").first()

    headers = {"Authorization": f"Bearer {token_a}"}
    malicious_payload = {
        "input_type": "text_paste",
        "content": "Trying to impersonate victim user.",
        "user_id": str(victim_user.id),
    }

    response = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json=malicious_payload,
        headers=headers,
    )
    assert response.status_code == 201

    job_id = uuid.UUID(response.json()["id"])
    job = db.query(Job).filter(Job.id == job_id).first()
    assert job.user_id == legit_user.id
    assert job.user_id != victim_user.id


# ==========================================
# Milestone 6: Job Retrieval & Status Tests
# ==========================================

@pytest.mark.anyio
async def test_get_job_unauthenticated(client, db):
    user = User(email="unauth_get@example.com", password_hash="hash")
    db.add(user)
    db.commit()
    job = Job(user_id=user.id, input_type="text_paste", raw_transcript="Sample transcript text.", status="pending")
    db.add(job)
    db.commit()

    response = await client.get(f"{settings.API_V1_STR}/jobs/{job.id}")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_job_invalid_token(client, db):
    user = User(email="invalid_token_get@example.com", password_hash="hash")
    db.add(user)
    db.commit()
    job = Job(user_id=user.id, input_type="text_paste", raw_transcript="Sample transcript text.", status="pending")
    db.add(job)
    db.commit()

    headers = {"Authorization": "Bearer invalid.jwt.token"}
    response = await client.get(f"{settings.API_V1_STR}/jobs/{job.id}", headers=headers)
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_job_expired_token(client, db):
    from datetime import timedelta
    from app.core.security import create_access_token

    user = User(email="expired_token_get@example.com", password_hash="hash")
    db.add(user)
    db.commit()
    job = Job(user_id=user.id, input_type="text_paste", raw_transcript="Sample transcript text.", status="pending")
    db.add(job)
    db.commit()

    expired_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=-10),
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await client.get(f"{settings.API_V1_STR}/jobs/{job.id}", headers=headers)
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_job_invalid_uuid_format(client):
    token = await register_and_get_token(client, email="invalid_uuid_get@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"{settings.API_V1_STR}/jobs/not-a-valid-uuid", headers=headers)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_job_nonexistent_uuid(client):
    token = await register_and_get_token(client, email="nonexistent_uuid_get@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    fake_id = str(uuid.uuid4())
    response = await client.get(f"{settings.API_V1_STR}/jobs/{fake_id}", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


@pytest.mark.anyio
async def test_get_job_ownership_isolation(client, db):
    token_a = await register_and_get_token(client, email="retrieval_user_a@example.com")
    token_b = await register_and_get_token(client, email="retrieval_user_b@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a job
    res_create = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "text_paste", "content": "Private confidential strategy transcript for User A."},
        headers=headers_a,
    )
    assert res_create.status_code == 201
    job_id = res_create.json()["id"]

    # User A retrieves own job -> 200
    res_a = await client.get(f"{settings.API_V1_STR}/jobs/{job_id}", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["id"] == job_id
    assert res_a.json()["status"] == "pending"

    # User B attempts to retrieve User A's job -> 404 Not Found (prevents enumeration)
    res_b = await client.get(f"{settings.API_V1_STR}/jobs/{job_id}", headers=headers_b)
    assert res_b.status_code == 404
    assert res_b.json()["detail"] == "Job not found"


@pytest.mark.anyio
async def test_get_job_all_lifecycle_states(client, db):
    from datetime import datetime, timezone

    token = await register_and_get_token(client, email="states_user@example.com")
    user = db.query(User).filter(User.email == "states_user@example.com").first()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Pending state
    job_pending = Job(user_id=user.id, input_type="text_paste", raw_transcript="Transcript pending.", status="pending")
    db.add(job_pending)
    db.commit()
    res_pending = await client.get(f"{settings.API_V1_STR}/jobs/{job_pending.id}", headers=headers)
    assert res_pending.status_code == 200
    data_pending = res_pending.json()
    assert data_pending["status"] == "pending"
    assert data_pending["result"] is None
    assert data_pending["completed_at"] is None
    assert data_pending["retry_count"] == 0

    # 2. Processing state
    job_processing = Job(user_id=user.id, input_type="txt_file", raw_transcript="Transcript processing.", status="processing", retry_count=1)
    db.add(job_processing)
    db.commit()
    res_processing = await client.get(f"{settings.API_V1_STR}/jobs/{job_processing.id}", headers=headers)
    assert res_processing.status_code == 200
    data_proc = res_processing.json()
    assert data_proc["status"] == "processing"
    assert data_proc["result"] is None
    assert data_proc["completed_at"] is None
    assert data_proc["retry_count"] == 1

    # 3. Complete state
    now_utc = datetime.now(timezone.utc)
    job_complete = Job(
        user_id=user.id,
        input_type="pdf_file",
        raw_transcript="Transcript completed.",
        status="complete",
        result={
            "processor": "clarityai-pipeline",
            "version": "0.3.0",
            "job_id": "test_id",
            "metadata": {"character_count": 21, "word_count": 2, "line_count": 1},
            "ai_analysis": {
                "summary": "Completed meeting summary",
                "key_points": ["Point 1"],
                "action_items": [],
                "sentiment": "neutral",
            },
            "llm_usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
        },
        completed_at=now_utc,
        retry_count=0,
        processing_started_at=now_utc,
        processing_duration_ms=450,
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_input_tokens=100,
        llm_output_tokens=50,
        llm_total_tokens=150,
    )
    db.add(job_complete)
    db.commit()
    res_complete = await client.get(f"{settings.API_V1_STR}/jobs/{job_complete.id}", headers=headers)
    assert res_complete.status_code == 200
    data_comp = res_complete.json()
    assert data_comp["status"] == "complete"
    assert data_comp["result"]["processor"] == "clarityai-pipeline"
    assert data_comp["result"]["version"] == "0.3.0"
    assert data_comp["result"]["metadata"]["word_count"] == 2
    assert data_comp["result"]["ai_analysis"]["summary"] == "Completed meeting summary"
    assert data_comp["completed_at"] is not None
    assert data_comp["processing_duration_ms"] == 450
    assert data_comp["llm_provider"] == "openai"
    assert data_comp["llm_total_tokens"] == 150

    # 4. Failed state
    job_failed = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Transcript failed.",
        status="failed",
        error_code="PROCESSING_ERROR",
        processing_duration_ms=120,
        result={"error": {"code": "PROCESSING_ERROR", "message": "An unexpected error occurred during job processing"}},
        retry_count=3,
    )
    db.add(job_failed)
    db.commit()
    res_failed = await client.get(f"{settings.API_V1_STR}/jobs/{job_failed.id}", headers=headers)
    assert res_failed.status_code == 200
    data_fail = res_failed.json()
    assert data_fail["status"] == "failed"
    assert data_fail["error_code"] == "PROCESSING_ERROR"
    assert data_fail["processing_duration_ms"] == 120
    assert data_fail["result"]["error"]["code"] == "PROCESSING_ERROR"
    assert data_fail["retry_count"] == 3


@pytest.mark.anyio
async def test_get_job_privacy_response_schema(client, db):
    token = await register_and_get_token(client, email="privacy_user@example.com")
    user = db.query(User).filter(User.email == "privacy_user@example.com").first()
    headers = {"Authorization": f"Bearer {token}"}

    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="SUPER_SECRET_SENSITIVE_TRANSCRIPT_CONTENT_NEVER_LEAK",
        status="pending",
    )
    db.add(job)
    db.commit()

    response = await client.get(f"{settings.API_V1_STR}/jobs/{job.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Exact expected public fields for M9
    allowed_fields = {
        "id",
        "input_type",
        "status",
        "result",
        "retry_count",
        "created_at",
        "completed_at",
        "processing_started_at",
        "processing_duration_ms",
        "llm_provider",
        "llm_model",
        "llm_input_tokens",
        "llm_output_tokens",
        "llm_total_tokens",
        "error_code",
    }
    assert set(data.keys()) == allowed_fields

    # Verify sensitive data is absent
    assert "raw_transcript" not in data
    assert "password_hash" not in data
    assert "SUPER_SECRET" not in str(data)


@pytest.mark.anyio
async def test_get_job_redis_independence(client, db, monkeypatch):
    import redis

    token = await register_and_get_token(client, email="redis_indep_user@example.com")
    user = db.query(User).filter(User.email == "redis_indep_user@example.com").first()
    headers = {"Authorization": f"Bearer {token}"}

    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Testing direct PostgreSQL read without Redis.",
        status="complete",
        result={
            "processor": "clarityai-pipeline",
            "version": "0.3.0",
            "job_id": "test_indep",
            "metadata": {"character_count": 45, "word_count": 6, "line_count": 1},
            "ai_analysis": None,
        },
        processing_duration_ms=250,
    )
    db.add(job)
    db.commit()

    # Mock Redis connection to raise error if accessed
    def fail_redis(*args, **kwargs):
        raise redis.ConnectionError("Redis is completely unavailable")

    monkeypatch.setattr("redis.from_url", fail_redis)

    response = await client.get(f"{settings.API_V1_STR}/jobs/{job.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "complete"
    assert response.json()["result"]["processor"] == "clarityai-pipeline"
    assert response.json()["processing_duration_ms"] == 250


@pytest.mark.anyio
async def test_job_create_worker_process_and_retrieve_e2e(client, db, monkeypatch):
    from app.processing import create_default_pipeline
    from app.llm.fake_provider import FakeLLMProvider
    from app.worker.tasks import process_job
    import app.worker.tasks as tasks_module

    test_pipeline = create_default_pipeline(llm_provider=FakeLLMProvider())
    monkeypatch.setattr(tasks_module, "_pipeline_override", test_pipeline)

    token = await register_and_get_token(client, email="e2e_pipeline_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    transcript = "   Executive meeting: Approved cloud infrastructure budget and headcount for Q3.   "
    res_create = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "text_paste", "content": transcript},
        headers=headers,
    )
    assert res_create.status_code == 201
    job_id = res_create.json()["id"]

    # Verify initial pending state
    res_pending = await client.get(f"{settings.API_V1_STR}/jobs/{job_id}", headers=headers)
    assert res_pending.status_code == 200
    assert res_pending.json()["status"] == "pending"
    assert res_pending.json()["processing_duration_ms"] is None

    # Worker processes the job through M9 pipeline
    process_job.apply(args=[job_id]).get()

    # Verify completed state with M12 pipeline result and observability columns
    res_completed = await client.get(f"{settings.API_V1_STR}/jobs/{job_id}", headers=headers)
    assert res_completed.status_code == 200
    comp_data = res_completed.json()
    assert comp_data["status"] == "complete"
    assert comp_data["result"]["processor"] == "clarityai-pipeline"
    assert comp_data["result"]["version"] == "0.6.0"
    assert comp_data["result"]["job_id"] == job_id
    assert comp_data["result"]["metadata"]["word_count"] == 10
    assert comp_data["result"]["metadata"]["line_count"] == 1
    assert comp_data["result"]["chunking_metadata"] is not None
    assert comp_data["result"]["chunking_metadata"]["chunk_count"] >= 1
    assert comp_data["result"]["retrieval_metadata"] is not None
    assert comp_data["result"]["retrieval_metadata"]["retrieved_count"] >= 1
    assert comp_data["result"]["ai_analysis"] is not None
    assert comp_data["result"]["ai_analysis"]["sentiment"] == "positive"
    assert len(comp_data["result"]["ai_analysis"]["action_items"]) == 2
    assert len(comp_data["result"]["ai_analysis"]["decisions"]) >= 1
    assert len(comp_data["result"]["ai_analysis"]["risks"]) >= 1
    assert len(comp_data["result"]["ai_analysis"]["open_questions"]) >= 1



    assert comp_data["completed_at"] is not None
    assert comp_data["processing_started_at"] is not None
    assert isinstance(comp_data["processing_duration_ms"], int)
    assert comp_data["processing_duration_ms"] >= 0
    assert comp_data["llm_provider"] == "fake"
    assert comp_data["llm_model"] == "fake-model"
    assert comp_data["llm_input_tokens"] == 100
    assert comp_data["llm_output_tokens"] == 50
    assert comp_data["llm_total_tokens"] == 150
    assert comp_data["error_code"] is None


@pytest.mark.anyio
async def test_job_failed_worker_retrieval_and_safe_error_exposure(client, db, monkeypatch):
    from app.processing import create_default_pipeline
    from app.llm.openai_provider import OpenAIProvider
    from app.worker.tasks import process_job
    import app.worker.tasks as tasks_module

    # Unconfigured OpenAI provider (no API key)
    unconfigured_pipeline = create_default_pipeline(llm_provider=OpenAIProvider(api_key=""))
    monkeypatch.setattr(tasks_module, "_pipeline_override", unconfigured_pipeline)

    token = await register_and_get_token(client, email="failed_job_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    transcript = "Confidential sprint transcript containing secrets."
    res_create = await client.post(
        f"{settings.API_V1_STR}/jobs",
        json={"input_type": "text_paste", "content": transcript},
        headers=headers,
    )
    assert res_create.status_code == 201
    job_id = res_create.json()["id"]

    # Worker processing encounters non-retryable LLMConfigurationError
    try:
        process_job.apply(args=[job_id], throw=True)
    except Exception:
        pass

    # Retrieve failed job
    res_failed = await client.get(f"{settings.API_V1_STR}/jobs/{job_id}", headers=headers)
    assert res_failed.status_code == 200
    data = res_failed.json()
    assert data["status"] == "failed"
    assert data["error_code"] == "LLM_CONFIGURATION_ERROR"
    assert data["result"] == {
        "error": {
            "code": "LLM_CONFIGURATION_ERROR",
            "message": "LLM service is improperly configured",
        }
    }
    # Raw transcript is NOT leaked in API response
    assert "raw_transcript" not in data
    assert transcript not in str(data)


# ==========================================
# Milestone 15: Paginated Job History Tests
# ==========================================

@pytest.mark.anyio
async def test_list_jobs_unauthenticated(client):
    response = await client.get(f"{settings.API_V1_STR}/jobs")
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_list_jobs_invalid_token(client):
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    response = await client.get(f"{settings.API_V1_STR}/jobs", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_list_jobs_expired_token(client):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await client.get(f"{settings.API_V1_STR}/jobs", headers=headers)
    assert response.status_code == 401


@pytest.mark.anyio
async def test_list_jobs_empty_history(client):
    token = await register_and_get_token(client, email="empty_history@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"{settings.API_V1_STR}/jobs", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] == 0
    assert data["pages"] == 0


@pytest.mark.anyio
async def test_list_jobs_single_job(client, db):
    token = await register_and_get_token(client, email="single_job@example.com")
    user = db.query(User).filter(User.email == "single_job@example.com").first()
    headers = {"Authorization": f"Bearer {token}"}

    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Single job test transcript.",
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    response = await client.get(f"{settings.API_V1_STR}/jobs", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["pages"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["id"] == str(job.id)
    assert item["status"] == "pending"
    assert item["input_type"] == "text_paste"


@pytest.mark.anyio
async def test_list_jobs_multiple_jobs_all_returned_with_large_page_size(client, db):
    token = await register_and_get_token(client, email="multi_job@example.com")
    user = db.query(User).filter(User.email == "multi_job@example.com").first()
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(5):
        db.add(
            Job(
                user_id=user.id,
                input_type="text_paste",
                raw_transcript=f"Transcript number {i}",
                status="pending",
            )
        )
    db.commit()

    response = await client.get(f"{settings.API_V1_STR}/jobs?page=1&page_size=50", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert data["pages"] == 1
    assert len(data["items"]) == 5


@pytest.mark.anyio
async def test_list_jobs_pagination_25_jobs(client, db):
    token = await register_and_get_token(client, email="paginated_25@example.com")
    user = db.query(User).filter(User.email == "paginated_25@example.com").first()
    headers = {"Authorization": f"Bearer {token}"}

    base_time = datetime.now(timezone.utc)
    for i in range(25):
        db.add(
            Job(
                user_id=user.id,
                input_type="text_paste",
                raw_transcript=f"Batch transcript {i}",
                status="pending",
                created_at=base_time + timedelta(seconds=i),
            )
        )
    db.commit()

    # Page 1
    res1 = await client.get(f"{settings.API_V1_STR}/jobs?page=1&page_size=10", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["page"] == 1
    assert data1["page_size"] == 10
    assert data1["total"] == 25
    assert data1["pages"] == 3
    assert len(data1["items"]) == 10
    ids_p1 = [item["id"] for item in data1["items"]]

    # Page 2
    res2 = await client.get(f"{settings.API_V1_STR}/jobs?page=2&page_size=10", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["page"] == 2
    assert data2["page_size"] == 10
    assert data2["total"] == 25
    assert data2["pages"] == 3
    assert len(data2["items"]) == 10
    ids_p2 = [item["id"] for item in data2["items"]]

    # Page 3
    res3 = await client.get(f"{settings.API_V1_STR}/jobs?page=3&page_size=10", headers=headers)
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["page"] == 3
    assert data3["page_size"] == 10
    assert data3["total"] == 25
    assert data3["pages"] == 3
    assert len(data3["items"]) == 5
    ids_p3 = [item["id"] for item in data3["items"]]

    # No duplicates across pages and all 25 accounted for
    all_ids = ids_p1 + ids_p2 + ids_p3
    assert len(all_ids) == 25
    assert len(set(all_ids)) == 25


@pytest.mark.anyio
async def test_list_jobs_deterministic_ordering(client, db):
    token = await register_and_get_token(client, email="ordering_test@example.com")
    user = db.query(User).filter(User.email == "ordering_test@example.com").first()
    headers = {"Authorization": f"Bearer {token}"}

    t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Insert out of order
    j_mid = Job(user_id=user.id, input_type="text_paste", raw_transcript="mid", created_at=t1)
    j_old = Job(user_id=user.id, input_type="text_paste", raw_transcript="old", created_at=t0)
    j_new = Job(user_id=user.id, input_type="text_paste", raw_transcript="new", created_at=t2)
    db.add_all([j_mid, j_old, j_new])
    db.commit()

    response = await client.get(f"{settings.API_V1_STR}/jobs?page=1&page_size=10", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 3
    assert items[0]["id"] == str(j_new.id)
    assert items[1]["id"] == str(j_mid.id)
    assert items[2]["id"] == str(j_old.id)


@pytest.mark.anyio
async def test_list_jobs_tie_breaker_ordering_by_id_desc(client, db):
    token = await register_and_get_token(client, email="tiebreak_test@example.com")
    user = db.query(User).filter(User.email == "tiebreak_test@example.com").first()
    headers = {"Authorization": f"Bearer {token}"}

    fixed_time = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    id_smaller = uuid.UUID("11111111-1111-1111-1111-111111111111")
    id_larger = uuid.UUID("99999999-9999-9999-9999-999999999999")

    j1 = Job(id=id_smaller, user_id=user.id, input_type="text_paste", raw_transcript="first", created_at=fixed_time)
    j2 = Job(id=id_larger, user_id=user.id, input_type="text_paste", raw_transcript="second", created_at=fixed_time)
    db.add_all([j1, j2])
    db.commit()

    response = await client.get(f"{settings.API_V1_STR}/jobs?page=1&page_size=10", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    # Secondary tiebreaker id DESC puts id_larger first
    assert items[0]["id"] == str(id_larger)
    assert items[1]["id"] == str(id_smaller)


@pytest.mark.anyio
async def test_list_jobs_page_beyond_last_page(client, db):
    token = await register_and_get_token(client, email="beyond_page@example.com")
    user = db.query(User).filter(User.email == "beyond_page@example.com").first()
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(3):
        db.add(Job(user_id=user.id, input_type="text_paste", raw_transcript=f"Job {i}"))
    db.commit()

    response = await client.get(f"{settings.API_V1_STR}/jobs?page=10&page_size=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["page"] == 10
    assert data["page_size"] == 10
    assert data["total"] == 3
    assert data["pages"] == 1


@pytest.mark.parametrize(
    "invalid_query",
    [
        "page=0",
        "page=-1",
        "page_size=0",
        "page_size=-1",
        "page_size=101",
        "page=0&page_size=0",
        "page=-5&page_size=150",
    ],
)
@pytest.mark.anyio
async def test_list_jobs_query_validation_422(client, invalid_query):
    token = await register_and_get_token(client, email="val_query@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"{settings.API_V1_STR}/jobs?{invalid_query}", headers=headers)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_jobs_ownership_isolation(client, db):
    token_a = await register_and_get_token(client, email="user_a@example.com")
    token_b = await register_and_get_token(client, email="user_b@example.com")

    user_a = db.query(User).filter(User.email == "user_a@example.com").first()
    user_b = db.query(User).filter(User.email == "user_b@example.com").first()

    job_a1 = Job(user_id=user_a.id, input_type="text_paste", raw_transcript="User A transcript 1")
    job_a2 = Job(user_id=user_a.id, input_type="text_paste", raw_transcript="User A transcript 2")
    job_b1 = Job(user_id=user_b.id, input_type="text_paste", raw_transcript="User B transcript 1")

    db.add_all([job_a1, job_a2, job_b1])
    db.commit()

    # User A check
    res_a = await client.get(f"{settings.API_V1_STR}/jobs", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["total"] == 2
    ids_a = {item["id"] for item in data_a["items"]}
    assert ids_a == {str(job_a1.id), str(job_a2.id)}
    assert str(job_b1.id) not in ids_a

    # User B check
    res_b = await client.get(f"{settings.API_V1_STR}/jobs", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["total"] == 1
    ids_b = {item["id"] for item in data_b["items"]}
    assert ids_b == {str(job_b1.id)}
    assert str(job_a1.id) not in ids_b
    assert str(job_a2.id) not in ids_b


@pytest.mark.anyio
async def test_list_jobs_privacy_no_raw_transcript_or_passwords(client, db):
    token = await register_and_get_token(client, email="privacy_list@example.com")
    user = db.query(User).filter(User.email == "privacy_list@example.com").first()
    headers = {"Authorization": f"Bearer {token}"}

    secret_raw_text = "CONFIDENTIAL_TOP_SECRET_TRANSCRIPT_12345"
    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript=secret_raw_text,
        status="complete",
        result={"processor": "clarityai-pipeline", "version": "0.6.0"},
    )
    db.add(job)
    db.commit()

    response = await client.get(f"{settings.API_V1_STR}/jobs", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert "raw_transcript" not in item
    assert "password_hash" not in item
    assert secret_raw_text not in str(data)


@pytest.mark.anyio
async def test_list_jobs_result_serialization_integrity(client, db):
    token = await register_and_get_token(client, email="serialization_list@example.com")
    user = db.query(User).filter(User.email == "serialization_list@example.com").first()
    headers = {"Authorization": f"Bearer {token}"}

    intelligence_result = {
        "processor": "clarityai-pipeline",
        "version": "0.6.0",
        "job_id": "test-job-id",
        "metadata": {"character_count": 100, "word_count": 20, "line_count": 2},
        "chunking_metadata": {"chunk_count": 1, "chunk_size_chars": 4000, "chunk_overlap_chars": 400},
        "retrieval_metadata": {"retrieval_strategy": "keyword", "retrieved_count": 1, "query": "meeting"},
        "ai_analysis": {
            "summary": "Sprint summary",
            "key_points": ["Point 1"],
            "decisions": [{"decision": "Migrate DB", "rationale": "HA"}],
            "action_items": [{"task": "Deploy", "owner": "Alice"}],
            "risks": [{"description": "Lag", "severity": "low"}],
            "open_questions": [{"question": "Rollout time?", "owner": None}],
            "sentiment": "positive",
        },
        "llm_usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        "llm_provider": "fake",
        "llm_model": "fake-model",
    }

    job = Job(
        user_id=user.id,
        input_type="text_paste",
        raw_transcript="Meeting text",
        status="complete",
        result=intelligence_result,
        llm_provider="fake",
        llm_model="fake-model",
        llm_input_tokens=100,
        llm_output_tokens=50,
        llm_total_tokens=150,
    )
    db.add(job)
    db.commit()

    response = await client.get(f"{settings.API_V1_STR}/jobs", headers=headers)
    assert response.status_code == 200
    data = response.json()
    item = data["items"][0]
    assert item["result"]["processor"] == "clarityai-pipeline"
    assert item["result"]["version"] == "0.6.0"
    assert item["result"]["ai_analysis"]["sentiment"] == "positive"
    assert item["llm_provider"] == "fake"
    assert item["llm_total_tokens"] == 150






