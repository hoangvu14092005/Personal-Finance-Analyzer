"""Re-export storage primitives từ `pfa_shared.storage` (M5).

Code API cũ import từ `app.integrations.storage.base` vẫn hoạt động.
Nguồn duy nhất ở `backend/shared/pfa_shared/storage/base.py`."""
from __future__ import annotations

from pfa_shared.storage.base import (
    StorageNotFoundError,
    StorageService,
    StoredObject,
)

__all__ = ["StorageNotFoundError", "StorageService", "StoredObject"]
