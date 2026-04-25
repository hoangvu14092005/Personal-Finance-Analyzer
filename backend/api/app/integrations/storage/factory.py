from __future__ import annotations

from pathlib import Path

from app.integrations.storage.base import StorageService
from app.integrations.storage.local import LocalStorageService

# Storage root cho local/test backend; tách thành module-level constant để
# có thể override khi test hoặc tune theo deployment.
DEFAULT_LOCAL_STORAGE_ROOT = Path("data/receipts")


def get_storage_service() -> StorageService:
    """Trả về implementation `StorageService`.

    Hiện tại MVP chỉ có `LocalStorageService`. Khi mở MinIO/S3 (Phase 5+),
    thêm nhánh dispatch theo `settings.app_env` hoặc cấu hình storage backend
    riêng (`storage_backend = "local" | "s3"`) thay vì if-else trùng lặp.
    """
    return LocalStorageService(root_dir=DEFAULT_LOCAL_STORAGE_ROOT)
