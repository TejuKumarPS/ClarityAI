import uuid
from datetime import datetime, timedelta, timezone
import pytest
import jwt
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User


@pytest.mark.anyio
async def test_register_user_success(client, db):
    payload = {
        "email": "alice@example.com",
        "password": "StrongPassword123!",
    }
    response = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert uuid.UUID(data["id"])
    assert data["email"] == "alice@example.com"
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.anyio
async def test_register_user_password_hashed_bcrypt(client, db):
    payload = {
        "email": "hashcheck@example.com",
        "password": "SecretPassword123!",
    }
    response = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
    assert response.status_code == 201

    user_id = uuid.UUID(response.json()["id"])
    user = db.query(User).filter(User.id == user_id).first()
    assert user is not None
    assert user.password_hash != "SecretPassword123!"
    assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")
    assert verify_password("SecretPassword123!", user.password_hash)


@pytest.mark.anyio
async def test_register_user_duplicate_email(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
    }
    response1 = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
    assert response1.status_code == 201

    response2 = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"].lower()


@pytest.mark.anyio
async def test_register_user_case_normalization(client):
    payload1 = {
        "email": "MixedCase@Example.Com",
        "password": "Password123!",
    }
    response1 = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload1)
    assert response1.status_code == 201
    assert response1.json()["email"] == "mixedcase@example.com"

    payload2 = {
        "email": "mixedcase@example.com",
        "password": "DifferentPassword123!",
    }
    response2 = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload2)
    assert response2.status_code == 409


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_password",
    [
        "",
        "short",
        "1234567",
        "   ",
        "        ",
    ],
)
async def test_register_user_invalid_password(client, invalid_password):
    payload = {
        "email": "invalidpass@example.com",
        "password": invalid_password,
    }
    response = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_login_user_success(client):
    register_payload = {
        "email": "loginuser@example.com",
        "password": "LoginPassword123!",
    }
    await client.post(f"{settings.API_V1_STR}/auth/register", json=register_payload)

    login_payload = {
        "email": "loginuser@example.com",
        "password": "LoginPassword123!",
    }
    response = await client.post(f"{settings.API_V1_STR}/auth/login", json=login_payload)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_user_case_insensitive_email(client):
    register_payload = {
        "email": "caseuser@example.com",
        "password": "LoginPassword123!",
    }
    await client.post(f"{settings.API_V1_STR}/auth/register", json=register_payload)

    login_payload = {
        "email": "CASEUSER@EXAMPLE.COM",
        "password": "LoginPassword123!",
    }
    response = await client.post(f"{settings.API_V1_STR}/auth/login", json=login_payload)
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.anyio
async def test_login_user_incorrect_password(client):
    register_payload = {
        "email": "wrongpass@example.com",
        "password": "CorrectPassword123!",
    }
    await client.post(f"{settings.API_V1_STR}/auth/register", json=register_payload)

    login_payload = {
        "email": "wrongpass@example.com",
        "password": "IncorrectPassword123!",
    }
    response = await client.post(f"{settings.API_V1_STR}/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.anyio
async def test_login_user_nonexistent_email(client):
    login_payload = {
        "email": "doesnotexist@example.com",
        "password": "SomePassword123!",
    }
    response = await client.post(f"{settings.API_V1_STR}/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.anyio
async def test_me_protected_endpoint_success(client):
    register_payload = {
        "email": "meuser@example.com",
        "password": "MySecretPassword123!",
    }
    reg_res = await client.post(f"{settings.API_V1_STR}/auth/register", json=register_payload)
    user_id = reg_res.json()["id"]

    login_res = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": "meuser@example.com", "password": "MySecretPassword123!"},
    )
    token = login_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
    assert me_res.status_code == 200

    data = me_res.json()
    assert data["id"] == user_id
    assert data["email"] == "meuser@example.com"
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.anyio
async def test_me_missing_token(client):
    response = await client.get(f"{settings.API_V1_STR}/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_me_malformed_token(client):
    headers = {"Authorization": "Bearer not.a.valid.jwt.token"}
    response = await client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_me_invalid_signature(client):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    wrong_secret_token = jwt.encode(payload, "wrong-secret-key-12345678901234567890", algorithm="HS256")

    headers = {"Authorization": f"Bearer {wrong_secret_token}"}
    response = await client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_me_expired_token(client):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_me_missing_sub_claim(client):
    now = datetime.now(timezone.utc)
    payload = {
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token_without_sub = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    headers = {"Authorization": f"Bearer {token_without_sub}"}
    response = await client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_me_invalid_uuid_sub(client):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "not-a-valid-uuid",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token_bad_sub = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    headers = {"Authorization": f"Bearer {token_bad_sub}"}
    response = await client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_me_nonexistent_user_sub(client):
    random_user_id = str(uuid.uuid4())
    token = create_access_token(subject=random_user_id)

    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_settings_production_requires_strong_secret():
    from app.core.config import Settings
    with pytest.raises(ValueError):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="dev_insecure_jwt_secret_key_clarityai_development_only_2026",
            _env_file=None,
        )


def test_settings_missing_secret_fails():
    from app.core.config import Settings
    with pytest.raises(Exception):
        Settings(
            ENVIRONMENT="development",
            JWT_SECRET_KEY="",
            _env_file=None,
        )

