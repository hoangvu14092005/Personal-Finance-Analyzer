from __future__ import annotations

from functools import lru_cache  # cache kết quả để tránh đọc config nhiều lần
from typing import Literal

from pfa_shared.enums import AppEnv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        default="postgresql+psycopg://pfa:pfa@localhost:5432/pfa", # postgresql+psycopg://user:password@host:port/database
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    s3_endpoint: str = "http://localhost:9000"  # MinIO endpoint (local)
    s3_region: str = "us-east-1" 
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_private: str = "pfa-receipts"
    ocr_provider: str = "mock"
    ocr_timeout_ms: int = 8000
    ocr_max_file_size_mb: int = 10

    request_id_header: str = "X-Request-ID"

    jwt_secret: str = "change-me-in-prod-please-use-at-least-32-chars"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    session_cookie_name: str = "pfa_session"
    # secure=True: cookie chỉ gửi qua HTTPS; False để dev local trên HTTP.
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cors_origins: list[str] = [
        "http://localhost:3000", # Frontend dev server
        "http://127.0.0.1:3000", 
    ]

    # CORS Origin: danh sách domain được phép gọi API từ trình duyệt.
    # field_validator chạy trước khi Pydantic gán giá trị vào field cors_origins.
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        # Validator này chạy trước khi Pydantic gán giá trị vào field cors_origins.
        # Mục đích: hỗ trợ nhiều định dạng input khác nhau từ biến môi trường.

        if isinstance(value, str):
            # Nếu value là string (ví dụ từ .env: CORS_ORIGINS="http://localhost:3000,http://localhost:4000")
            # thì tách theo dấu phẩy và loại bỏ khoảng trắng thừa ở đầu/cuối mỗi phần tử.
            return [item.strip() for item in value.split(",") if item.strip()]

        if isinstance(value, list):
            # Nếu value đã là list (ví dụ được truyền trực tiếp trong code),
            # thì ép kiểu từng phần tử về string và loại bỏ khoảng trắng thừa.
            return [str(item).strip() for item in value if str(item).strip()]

        # Fallback: nếu value không phải string hay list (ví dụ None hoặc kiểu không hợp lệ),
        # trả về danh sách mặc định cho môi trường local.
        return ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
