from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
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
    def extract_text(self, file_path: Path) -> OCRRawResult:
        ...

    def normalize_receipt(self, raw: OCRRawResult) -> OCRNormalizedReceipt:
        ...


class MockOCRProvider:
    def extract_text(self, file_path: Path) -> OCRRawResult:
        stem = file_path.stem
        return OCRRawResult(
            provider="mock",
            raw_text=f"Receipt text extracted from {stem}",
            confidence=0.92,
        )

    def normalize_receipt(self, raw: OCRRawResult) -> OCRNormalizedReceipt:
        return OCRNormalizedReceipt(
            merchant="Mock Mart",
            transaction_date="2026-03-30",
            total_amount=Decimal("125000.00"),
            currency="VND",
        )


def get_ocr_provider() -> OCRProvider:
    return MockOCRProvider()
