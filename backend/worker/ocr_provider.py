"""OCR provider abstraction (M5 refactor).

Trước M5: `extract_text(file_path: Path)` — bind chặt vào local FS, worker
phải biết physical path. Sau M5: `extract_text(content: bytes, source_hint)`
— provider chỉ thấy bytes, worker dùng storage adapter để download bytes
từ local hoặc S3.

`source_hint` (optional) là filename hoặc storage_key gốc, dùng cho mock
log và debugging — không phải để mở file.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OCRRawResult:
    provider: str
    raw_text: str
    confidence: float


@dataclass(frozen=True, slots=True)
class OCRNormalizedReceipt:
    merchant: str
    transaction_date: str
    total_amount: Decimal
    currency: str


class OCRProvider(Protocol):
    def extract_text(self, content: bytes, source_hint: str = "") -> OCRRawResult:
        ...

    def normalize_receipt(self, raw: OCRRawResult) -> OCRNormalizedReceipt:
        ...


class MockOCRProvider:
    def extract_text(self, content: bytes, source_hint: str = "") -> OCRRawResult:  # noqa: ARG002
        # Mock: dùng source_hint làm tên file giả trong raw_text.
        # `content` không được parse — chỉ lưu kích thước để verify đã đọc bytes.
        label = source_hint or f"<{len(content)} bytes>"
        return OCRRawResult(
            provider="mock",
            raw_text=f"Receipt text extracted from {label}",
            confidence=0.92,
        )

    def normalize_receipt(self, raw: OCRRawResult) -> OCRNormalizedReceipt:  # noqa: ARG002
        return OCRNormalizedReceipt(
            merchant="Mock Mart",
            transaction_date="2026-03-30",
            total_amount=Decimal("125000.00"),
            currency="VND",
        )


def get_ocr_provider() -> OCRProvider:
    return MockOCRProvider()
