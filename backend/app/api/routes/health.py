from fastapi import APIRouter

from app.config.settings import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "service": "rupeeradar-api",
        "llm_provider": "groq",
        "llm_configured": settings.llm_enabled,
    }
