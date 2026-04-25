"""Re-export entities từ `pfa_shared.entities` để code API cũ không phải đổi
import path. Nguồn duy nhất ở `backend/shared/pfa_shared/entities.py` (M5)."""
from __future__ import annotations

from pfa_shared.entities import (
    Budget,
    Category,
    InsightSnapshot,
    OcrResult,
    ReceiptUpload,
    Transaction,
    User,
    UserMerchantMapping,
)

__all__ = [
    "Budget",
    "Category",
    "InsightSnapshot",
    "OcrResult",
    "ReceiptUpload",
    "Transaction",
    "User",
    "UserMerchantMapping",
]
