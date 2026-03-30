from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.integrations.storage.base import StorageService
from app.integrations.storage.local import LocalStorageService


def get_storage_service() -> StorageService:
    settings = get_settings()
    storage_root = Path("data/receipts")

    if settings.app_env.value in {"local", "test"}:
        return LocalStorageService(root_dir=storage_root)

    return LocalStorageService(root_dir=storage_root)
