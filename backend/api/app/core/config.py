from __future__ import annotations

from functools import lru_cache  # cache kết quả để tránh đọc config nhiều lần
from typing import Literal

from pfa_shared.enums import AppEnv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default placeholder JWT secret cho local/test. Settings validator sẽ reject
# giá trị này khi `app_env` ∈ {staging, prod} để fail-fast (M5).
DEFAULT_JWT_SECRET = "change-me-in-prod-please-use-at-least-32-chars"  # noqa: S105
MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    # Pydantic tự động đọc .env và map các biến environment vào field tương ứng.
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
        default="postgresql+psycopg://pfa:pfa@localhost:5433/pfa", # postgresql+psycopg://user:password@host:port/database
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    s3_endpoint: str = "http://localhost:9000"  # MinIO endpoint (local)
    s3_region: str = "us-east-1"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_private: str = "pfa-receipts"
    # Storage backend: "local" dùng `LocalStorageService` (filesystem),
    # "s3" dùng MinIO/S3 qua `S3StorageService`. Mặc định "local" cho dev.
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_root: str = "data/receipts"
    ocr_provider: str = "mock"
    ocr_timeout_ms: int = 8000
    ocr_max_file_size_mb: int = 10

    # Chat LLM provider (Phase 6 — AI Chatbot).
    chat_llm_base_url: str = "http://localhost:20128/v1"
    chat_llm_api_key: str = ""
    chat_llm_model: str = "cx/gpt-5.5"
    chat_llm_timeout_seconds: float = 60.0
    chat_max_history_messages: int = 40
    chat_rate_limit_per_minute: int = 10

    request_id_header: str = "X-Request-ID"

    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    session_cookie_name: str = "pfa_session"
    # secure=True: cookie chỉ gửi qua HTTPS; False để dev local trên HTTP.
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    # CORS Origins: comma-separated string để tương thích pydantic-settings v2
    # (list[str] bị JSON-decode trước khi field_validator chạy → lỗi với .env).
    # Dùng property `parsed_cors_origins` để lấy list[str].
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def parsed_cors_origins(self) -> list[str]:
        """Parse comma-separated CORS_ORIGINS thành list[str]."""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @model_validator(mode="after")
    def _enforce_production_secrets(self) -> Settings:
        """Fail-fast khi production secrets vẫn dùng giá trị placeholder.

        - Local/Test: vẫn cho phép `DEFAULT_JWT_SECRET` để dev khỏi cần set env.
        - Staging/Prod: bắt buộc `jwt_secret` phải khác default + đủ độ dài.
        - Staging/Prod: storage_backend phải là "s3" (không cho phép local FS).
        """
        if self.app_env in {AppEnv.STAGING, AppEnv.PROD}:
            if self.jwt_secret == DEFAULT_JWT_SECRET:
                raise ValueError(
                    "JWT_SECRET must be set to a non-default value in "
                    f"{self.app_env.value} environment. "
                    "Set the JWT_SECRET env var to a secure random string "
                    f"(>= {MIN_JWT_SECRET_LENGTH} chars).",
                )
            if len(self.jwt_secret) < MIN_JWT_SECRET_LENGTH:
                raise ValueError(
                    f"JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} "
                    f"characters in {self.app_env.value} environment, "
                    f"got {len(self.jwt_secret)} chars.",
                )
            if self.storage_backend != "s3":
                raise ValueError(
                    "STORAGE_BACKEND must be 's3' in "
                    f"{self.app_env.value} environment "
                    "(local filesystem storage is not supported).",
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
