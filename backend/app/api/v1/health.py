from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
def get_health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }
