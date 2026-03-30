from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pfa_shared.enums import AppEnv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnv = AppEnv.LOCAL
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = Field(
        default="postgresql+psycopg://pfa:pfa@localhost:5432/pfa",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    request_id_header: str = "X-Request-ID"

    jwt_secret: str = "change-me-in-prod-please-use-at-least-32-chars"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    session_cookie_name: str = "pfa_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
