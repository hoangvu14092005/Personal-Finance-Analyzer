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
