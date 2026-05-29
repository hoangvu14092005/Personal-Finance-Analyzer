"""Re-export entities từ `pfa_shared.entities` để code API cũ không phải đổi
import path. Nguồn duy nhất ở `backend/shared/pfa_shared/entities.py` (M5)."""
from __future__ import annotations

from pfa_shared.entities import (
    AuditLog,
    Budget,
    Category,
    ChatConversation,
    ChatMessage,
    Insight,
    InsightFeedback,
    InsightSnapshot,
    Invoice,
    InvoiceLineItem,
    Merchant,
    OcrResult,
    ReceiptLineItem,
    ReceiptTextChunk,
    ReceiptUpload,
    Transaction,
    User,
    UserMerchantAlias,
    UserMerchantMapping,
    UserSettings,
)

__all__ = [
    "AuditLog",
    "Budget",
    "Category",
    "ChatConversation",
    "ChatMessage",
    "Insight",
    "InsightFeedback",
    "InsightSnapshot",
    "Invoice",
    "InvoiceLineItem",
    "Merchant",
    "OcrResult",
    "ReceiptLineItem",
    "ReceiptTextChunk",
    "ReceiptUpload",
    "Transaction",
    "User",
    "UserMerchantAlias",
    "UserMerchantMapping",
    "UserSettings",
]
