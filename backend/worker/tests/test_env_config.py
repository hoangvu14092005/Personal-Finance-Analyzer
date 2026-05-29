from __future__ import annotations

from pfa_shared.config import CommonSettings


def test_worker_common_settings_read_runtime_env(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://pfa:pfa@localhost:5433/pfa")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("S3_BUCKET_PRIVATE", "pfa-receipts")
    monkeypatch.setenv("OCR_PROVIDER", "llm_vision")

    settings = CommonSettings.from_env()

    assert settings.database_url.endswith("localhost:5433/pfa")
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.storage_backend == "s3"
    assert settings.s3_endpoint == "http://localhost:9000"
    assert settings.s3_bucket_private == "pfa-receipts"
    assert settings.ocr_provider == "llm_vision"
