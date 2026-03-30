from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoredObject:
    storage_key: str
    size_bytes: int


class StorageService(Protocol):
    def upload_bytes(self, storage_key: str, content: bytes, content_type: str) -> StoredObject:
        ...

    def delete(self, storage_key: str) -> None:
        ...
