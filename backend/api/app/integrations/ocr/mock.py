from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.integrations.ocr.base import OCRNormalizedReceipt, OCRProvider, OCRRawResult


class MockOCRProvider(OCRProvider):
    def extract_text(self, file_path: Path) -> OCRRawResult:
        return OCRRawResult(
            provider="mock",
            raw_text=f"Receipt extracted from {file_path.name}",
            confidence=0.91,
        )

    def normalize_receipt(self, raw: OCRRawResult) -> OCRNormalizedReceipt:
        return OCRNormalizedReceipt(
            merchant="Mock Mart",
            transaction_date="2026-03-30",
            total_amount=Decimal("125000.00"),
            currency="VND",
        )
