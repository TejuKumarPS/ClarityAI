import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from app.core.config import settings
from app.main import app


async def register_and_get_token(client, email="ratelimit@example.com", password="Password123!"):
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
# Rate Limiting Tests
# ==========================================

@pytest.mark.anyio
async def test_rate_limit_exceeded_returns_429_json(client, monkeypatch):
    """Submitting more than RATE_LIMIT_JOBS_PER_HOUR triggers a 429 JSON response."""
    monkeypatch.setattr(settings, "RATE_LIMIT_JOBS_PER_HOUR", 2)

    # Reset the limiter storage to avoid cross-test contamination
    from app.core.rate_limit import limiter
    limiter.reset()

    token = await register_and_get_token(client, email="rate_limit_test@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"input_type": "text_paste", "content": "Transcript for rate limit testing purposes."}

    # First 2 requests should succeed
    for i in range(2):
        res = await client.post(f"{settings.API_V1_STR}/jobs", json=payload, headers=headers)
        assert res.status_code == 201, f"Request {i+1} should succeed, got {res.status_code}"

    # 3rd request should be rate limited
    res_limited = await client.post(f"{settings.API_V1_STR}/jobs", json=payload, headers=headers)
    assert res_limited.status_code == 429
    body = res_limited.json()
    assert "detail" in body
    assert body["detail"] == "Rate limit exceeded. Try again later."


@pytest.mark.anyio
async def test_rate_limit_per_user_isolation(client, monkeypatch):
    """Two different users can each submit up to the limit independently."""
    monkeypatch.setattr(settings, "RATE_LIMIT_JOBS_PER_HOUR", 2)

    from app.core.rate_limit import limiter
    limiter.reset()

    token_a = await register_and_get_token(client, email="ratelimit_user_a@example.com")
    token_b = await register_and_get_token(client, email="ratelimit_user_b@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    payload = {"input_type": "text_paste", "content": "Meeting transcript for per-user rate limit test."}

    # User A: 2 requests should succeed
    for i in range(2):
        res = await client.post(f"{settings.API_V1_STR}/jobs", json=payload, headers=headers_a)
        assert res.status_code == 201

    # User A: 3rd request should be rate limited
    res_a_limited = await client.post(f"{settings.API_V1_STR}/jobs", json=payload, headers=headers_a)
    assert res_a_limited.status_code == 429

    # User B: should still be able to submit (independent limit)
    for i in range(2):
        res = await client.post(f"{settings.API_V1_STR}/jobs", json=payload, headers=headers_b)
        assert res.status_code == 201

    # User B: 3rd request should be rate limited
    res_b_limited = await client.post(f"{settings.API_V1_STR}/jobs", json=payload, headers=headers_b)
    assert res_b_limited.status_code == 429


@pytest.mark.anyio
async def test_rate_limit_response_is_json_not_html(client, monkeypatch):
    """Confirm the 429 response is JSON with a detail field, not HTML."""
    monkeypatch.setattr(settings, "RATE_LIMIT_JOBS_PER_HOUR", 1)

    from app.core.rate_limit import limiter
    limiter.reset()

    token = await register_and_get_token(client, email="rate_json_check@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"input_type": "text_paste", "content": "Transcript for JSON format rate limit check."}

    # First request succeeds
    res = await client.post(f"{settings.API_V1_STR}/jobs", json=payload, headers=headers)
    assert res.status_code == 201

    # Second request triggers rate limit
    res_limited = await client.post(f"{settings.API_V1_STR}/jobs", json=payload, headers=headers)
    assert res_limited.status_code == 429

    # Verify it's JSON, not HTML
    content_type = res_limited.headers.get("content-type", "")
    assert "application/json" in content_type
    assert "<html" not in res_limited.text.lower()
    body = res_limited.json()
    assert isinstance(body, dict)
    assert "detail" in body
