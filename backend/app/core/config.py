import json
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    PROJECT_NAME: str = "ClarityAI"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/clarityai_dev"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    MAX_INPUT_FILE_SIZE_BYTES: int = 10 * 1024 * 1024
    MIN_TRANSCRIPT_LENGTH: int = 10

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_TASK_MAX_RETRIES: int = 3
    CELERY_TASK_RETRY_BACKOFF: int = 1



    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "Settings":
        if not self.JWT_SECRET_KEY or not self.JWT_SECRET_KEY.strip():
            raise ValueError("JWT_SECRET_KEY must be configured and cannot be empty")
        if self.ENVIRONMENT == "production":
            insecure_defaults = {
                "your-jwt-secret-key-min-32-chars",
                "dev_insecure_jwt_secret_key_clarityai_development_only_2026",
                "secret",
                "changeme",
            }
            if self.JWT_SECRET_KEY in insecure_defaults or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    "In production, JWT_SECRET_KEY must be an explicitly configured secret of at least 32 characters"
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

