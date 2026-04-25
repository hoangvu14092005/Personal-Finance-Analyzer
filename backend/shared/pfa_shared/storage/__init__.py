"""Storage adapters cho receipt files — chia sẻ giữa API và worker (M5).

Các backend hỗ trợ:
- `local`: filesystem dưới `storage_local_root` (dev/test).
- `s3`: MinIO/AWS S3 qua boto3 (staging/prod).

Cả API và worker đều dùng cùng adapter để tránh drift logic upload/download.
"""
from pfa_shared.storage.base import (
    StorageNotFoundError,
    StorageService,
    StorageSettings,
    StoredObject,
)
from pfa_shared.storage.factory import build_storage_service
from pfa_shared.storage.local import LocalStorageService
from pfa_shared.storage.s3 import S3StorageService

__all__ = [
    "LocalStorageService",
    "S3StorageService",
    "StorageNotFoundError",
    "StorageService",
    "StorageSettings",
    "StoredObject",
    "build_storage_service",
]
