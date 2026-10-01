"""Typed application settings loaded from environment variables.

No secret is read from source control.  Copy ``.env.example`` to ``.env`` for
local development and provide a strong ``SECRET_KEY`` outside development.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API."""

    app_name: str = "CalTracker API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = "sqlite:///./caltracker.db"
    secret_key: str = "change-me-in-a-local-env-file"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    ai_provider: Literal["mock", "openai"] = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: float = 20.0
    seed_demo_foods: bool = True
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_expiration(cls, value: int) -> int:
        if value < 5:
            raise ValueError("access_token_expire_minutes must be at least 5")
        return value

    @model_validator(mode="after")
    def validate_production_secret(self):
        if self.environment == "production" and len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY doit contenir au moins 32 caractères en production")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        """Return CORS origins without empty values or surrounding spaces."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Build settings once per process, which also makes tests easy to override."""

    return Settings()
