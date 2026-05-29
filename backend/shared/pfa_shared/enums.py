"""Enums dùng chung cho API và Worker."""
from __future__ import annotations

from enum import StrEnum


class AppEnv(StrEnum):
    """Environment: local/test/staging/prod."""
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"

    @classmethod
    def from_value(cls, value: str) -> AppEnv:
        """Parse string -> enum, fallback to LOCAL."""
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        return cls.LOCAL


class ServiceName(StrEnum):
    """Service names: api/worker."""
    API = "api"
    WORKER = "worker"


class ReceiptStatus(StrEnum):
    """Receipt OCR lifecycle: uploaded -> processing -> ready/failed.
    
    Frontend polls /receipts/{id}/status để track progress.
    """
    UPLOADED = "uploaded"      # File uploaded, chờ worker
    PROCESSING = "processing"  # Worker đang OCR
    READY = "ready"            # OCR xong, có kết quả
    FAILED = "failed"          # OCR lỗi, cần manual entry
