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
