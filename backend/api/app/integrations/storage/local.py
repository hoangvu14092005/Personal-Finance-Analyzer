from __future__ import annotations

from pathlib import Path

from app.integrations.storage.base import StorageService, StoredObject


class LocalStorageService(StorageService):
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir

    def upload_bytes(self, storage_key: str, content: bytes, content_type: str) -> StoredObject:
        file_path = self.root_dir / storage_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return StoredObject(storage_key=storage_key, size_bytes=len(content))

    def delete(self, storage_key: str) -> None:
        file_path = self.root_dir / storage_key
        if file_path.exists():
            file_path.unlink()
