from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from the project root (two levels up from this file: app/config/ → app/ → backend/ → project root)
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./rupeeradar.db"
    max_upload_size_mb: int = 10
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    session_ttl_hours: int = 24

    # Groq LLM (used from Phase 2 onward)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def llm_enabled(self) -> bool:
        return bool(self.groq_api_key.strip())


settings = Settings()
