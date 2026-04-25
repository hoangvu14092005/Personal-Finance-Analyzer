from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Kết quả upload thành công."""

    storage_key: str
    size_bytes: int


class StorageNotFoundError(Exception):
    """Raise khi storage_key không tồn tại trên backend (404 / NoSuchKey)."""


class StorageService(Protocol):
    """Interface chung cho local + S3. Sync API — caller wrap trong
    `asyncio.to_thread` nếu cần non-blocking."""

    def upload_bytes(self, storage_key: str, content: bytes, content_type: str) -> StoredObject:
        ...

    def download_bytes(self, storage_key: str) -> bytes:
        ...

    def delete(self, storage_key: str) -> None:
        ...


class StorageSettings(Protocol):
    """Protocol mô tả các field setting cần thiết cho storage adapter.

    Cả `app.core.config.Settings` (API) và `pfa_shared.config.CommonSettings`
    (worker) đều structural-match Protocol này.
    """

    storage_backend: Literal["local", "s3"]
    storage_local_root: str
    s3_endpoint: str
    s3_region: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket_private: str
