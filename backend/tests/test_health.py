import pytest
from app.core.config import settings


@pytest.mark.anyio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.PROJECT_NAME
    assert data["environment"] == settings.ENVIRONMENT
    assert data["version"] == "0.1.0"


@pytest.mark.anyio
async def test_versioned_health_endpoint(client):
    response = await client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.PROJECT_NAME
    assert data["environment"] == settings.ENVIRONMENT
    assert data["version"] == "0.1.0"


@pytest.mark.anyio
async def test_settings_loaded_from_environment():
    assert settings.PROJECT_NAME == "ClarityAI"
    assert settings.ENVIRONMENT == "development"
    assert settings.API_V1_STR == "/api/v1"
    assert "http://localhost:5173" in settings.CORS_ORIGINS


@pytest.mark.anyio
async def test_cors_allowed_origin(client):
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = await client.options("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.anyio
async def test_cors_get_request(client):
    headers = {"Origin": "http://localhost:5173"}
    response = await client.get("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


@pytest.mark.anyio
async def test_cors_disallowed_origin(client):
    headers = {
        "Origin": "http://malicious-site.com",
        "Access-Control-Request-Method": "GET",
    }
    response = await client.options("/health", headers=headers)
    assert response.headers.get("access-control-allow-origin") is None
