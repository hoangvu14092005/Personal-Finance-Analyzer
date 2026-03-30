from __future__ import annotations 

import os
from dataclasses import dataclass

from pfa_shared.enums import AppEnv


@dataclass(frozen=True, slots=True)
class CommonSettings:
    app_env: AppEnv
    log_level: str
    redis_url: str
    s3_endpoint: str
    s3_region: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket_private: str
    ocr_provider: str
    ocr_timeout_ms: int
    ocr_max_file_size_mb: int

    @classmethod
    def from_env(cls) -> "CommonSettings":
        env_value = os.getenv("APP_ENV", AppEnv.LOCAL.value)
        app_env = AppEnv.from_value(env_value)
        return cls(
            app_env=app_env,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            s3_endpoint=os.getenv("S3_ENDPOINT", "http://localhost:9000"),
            s3_region=os.getenv("S3_REGION", "us-east-1"),
            s3_access_key=os.getenv("S3_ACCESS_KEY", "minioadmin"),
            s3_secret_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
            s3_bucket_private=os.getenv("S3_BUCKET_PRIVATE", "pfa-receipts"),
            ocr_provider=os.getenv("OCR_PROVIDER", "mock"),
            ocr_timeout_ms=int(os.getenv("OCR_TIMEOUT_MS", "8000")),
            ocr_max_file_size_mb=int(os.getenv("OCR_MAX_FILE_SIZE_MB", "10")),
        )
