from __future__ import annotations

from pathlib import Path

from pfa_shared.storage.base import StorageService, StorageSettings
from pfa_shared.storage.local import LocalStorageService
from pfa_shared.storage.s3 import S3StorageService


def build_storage_service(settings: StorageSettings) -> StorageService:
    """Build storage adapter theo `settings.storage_backend`.

    Caller (API/worker) tự cache singleton (vd. qua `lru_cache`) nếu cần,
    để hàm này không phụ thuộc vào lifecycle của settings (test có thể
    override settings dễ dàng).
    """
    if settings.storage_backend == "s3":
        return S3StorageService(
            endpoint_url=settings.s3_endpoint,
            region=settings.s3_region,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket_private,
        )
    return LocalStorageService(root_dir=Path(settings.storage_local_root))
