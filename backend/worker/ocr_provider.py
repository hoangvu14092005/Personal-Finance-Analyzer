"""OCR provider abstraction (M5 refactor).

M5 change: extract_text(content: bytes) thay vì extract_text(file_path: Path)
→ Provider không biết storage backend (local/S3), chỉ nhận bytes.

MockOCRProvider: Fake OCR cho development, trả fixed values.
Production: GoogleVisionOCRProvider (chưa implement).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OCRRawResult:
    """Raw OCR output từ provider."""
    provider: str       # "mock" | "google"
    raw_text: str       # Full text extracted
    confidence: float   # 0.0 - 1.0


@dataclass(frozen=True, slots=True)
class OCRNormalizedReceipt:
    """Normalized receipt data sau khi parse raw_text."""
    merchant: str
    transaction_date: str  # ISO format "YYYY-MM-DD"
    total_amount: Decimal
    currency: str


class OCRProvider(Protocol):
    """Protocol cho OCR providers. Implement 2 methods này."""
    
    def extract_text(self, content: bytes, source_hint: str = "") -> OCRRawResult:
        """Extract text từ receipt image/PDF bytes.
        
        Args:
            content: File bytes (JPG/PNG/PDF)
            source_hint: Optional filename cho logging (không dùng để mở file)
        """
        ...

    def normalize_receipt(self, raw: OCRRawResult) -> OCRNormalizedReceipt:
        """Parse raw OCR text thành structured data."""
        ...


class MockOCRProvider:
    """Mock OCR provider cho development. Trả fixed fake data."""
    
    def extract_text(self, content: bytes, source_hint: str = "") -> OCRRawResult:  # noqa: ARG002
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
    """Factory function: trả OCR provider dựa trên env config.
    
    Hiện tại: chỉ có MockOCRProvider.
    TODO: Add GoogleVisionOCRProvider khi có API key.
    """
    return MockOCRProvider()
