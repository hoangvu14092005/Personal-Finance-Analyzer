from __future__ import annotations

from functools import lru_cache

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
