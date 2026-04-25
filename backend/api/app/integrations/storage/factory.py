from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from pfa_shared.storage import StorageService, build_storage_service


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    """Trả về implementation `StorageService` theo `settings.storage_backend`.

    Cache singleton qua `lru_cache`. Khi đổi settings trong test, gọi
    `get_storage_service.cache_clear()` (xem conftest fixture
    `_reset_storage_singleton`).
    """
    return build_storage_service(get_settings())
