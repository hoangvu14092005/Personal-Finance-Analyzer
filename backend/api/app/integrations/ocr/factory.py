from __future__ import annotations

from app.core.config import get_settings
from app.integrations.ocr.base import OCRProvider
from app.integrations.ocr.mock import MockOCRProvider


def get_ocr_provider() -> OCRProvider:
    settings = get_settings()
    if settings.ocr_provider == "mock":
        return MockOCRProvider()

    return MockOCRProvider()
