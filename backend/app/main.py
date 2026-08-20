from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_v1_router
from app.api.v1.health import get_health

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unversioned health check
app.add_api_route("/health", get_health, methods=["GET"], tags=["Health"])

# Versioned API routes
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
