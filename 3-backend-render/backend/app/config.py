"""Server-side environment configuration with Pydantic Settings and secret redaction."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # Fallback for environments without pydantic-settings installed
    BaseSettings = object  # type: ignore

    def Field(default=None, **_kwargs):  # type: ignore
        return default

    SettingsConfigDict = dict  # type: ignore


class AppSettings(BaseSettings):  # type: ignore[misc]
    """Centralized server configuration read strictly from environment variables."""

    APP_ENV: str = Field(default="development")
    APP_NAME: str = Field(default="NEXUS MEDIA AI")
    APP_VERSION: str = Field(default="0.1.0")
    LOG_LEVEL: str = Field(default="INFO")

    # Database (Supabase PostgreSQL / Session Pooler compatible)
    DATABASE_URL: str = Field(default="")
    DATABASE_SSL: str = Field(default="require")
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=10)
    DB_POOL_RECYCLE_SECONDS: int = Field(default=1800)

    # Supabase Server Variables
    SUPABASE_URL: str = Field(default="")
    SUPABASE_SECRET_KEY: str = Field(default="")

    # Authentication & JWT
    JWT_SECRET: str = Field(default="")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    # Origins, CORS & Rate Limiting
    ADMIN_ORIGIN: str = Field(default="http://localhost:3000")
    CORS_ALLOWED_ORIGINS: str = Field(default="http://localhost:3000")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=120)

    # Downstream Publishing & AI Integrations
    BLOG_ENDPOINT: str = Field(default="")
    BLOG_SIGNING_SECRET: str = Field(default="")
    CLOUDFLARE_WEBHOOK_SECRET: str = Field(default="")
    AI_PROVIDER: str = Field(default="gemini")
    AI_PROVIDER_API_KEY: str = Field(default="")
    PUBLISHING_MODE: str = Field(default="manual")
    PEXELS_API_KEY: str = Field(default="")
    UNSPLASH_ACCESS_KEY: str = Field(default="")

    # Auth bootstrap credentials
    ADMIN_EMAIL: str = Field(default="")
    ADMIN_PASSWORD_HASH: str = Field(default="")
    ADMIN_PASSWORD: str = Field(default="")

    if BaseSettings is not object:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore",
        )
    else:

        def __init__(self, **kwargs):
            for k in dir(self):
                if k.isupper():
                    setattr(self, k, kwargs.get(k, os.environ.get(k, getattr(self, k))))

    @property
    def is_database_configured(self) -> bool:
        raw = (self.DATABASE_URL or "").strip()
        if not raw or "YOUR_PASSWORD" in raw or "example.com" in raw:
            return False
        return raw.startswith(("postgresql://", "postgres://", "postgresql+asyncpg://"))

    @property
    def normalized_async_database_url(self) -> str:
        """Converts standard postgres:// or postgresql:// URLs to postgresql+asyncpg://."""
        raw = (self.DATABASE_URL or "").strip()
        if not self.is_database_configured:
            return ""
        if raw.startswith("postgres://"):
            return "postgresql+asyncpg://" + raw[len("postgres://") :]
        if raw.startswith("postgresql://"):
            return "postgresql+asyncpg://" + raw[len("postgresql://") :]
        return raw

    @property
    def allowed_cors_origins_list(self) -> List[str]:
        origins = set()
        if self.ADMIN_ORIGIN and self.ADMIN_ORIGIN.strip():
            origins.add(self.ADMIN_ORIGIN.strip())
        if self.CORS_ALLOWED_ORIGINS:
            for item in self.CORS_ALLOWED_ORIGINS.split(","):
                cleaned = item.strip()
                if cleaned and cleaned != "*":
                    origins.add(cleaned)
        if not origins:
            origins.add("http://localhost:3000")
        return sorted(origins)

    def redacted_summary(self) -> dict:
        """Safe diagnostic summary with all secrets redacted."""
        return {
            "app_env": self.APP_ENV,
            "app_name": self.APP_NAME,
            "version": self.APP_VERSION,
            "database_configured": self.is_database_configured,
            "database_ssl": self.DATABASE_SSL,
            "supabase_configured": bool(self.SUPABASE_URL and self.SUPABASE_SECRET_KEY),
            "jwt_secret_configured": bool(self.JWT_SECRET and len(self.JWT_SECRET) >= 32),
            "cors_allowed_origins": self.allowed_cors_origins_list,
            "secrets_redacted": "[REDACTED]",
        }


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
