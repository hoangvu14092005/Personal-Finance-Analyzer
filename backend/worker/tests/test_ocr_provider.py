from __future__ import annotations

from pathlib import Path

from ocr_provider import get_ocr_provider


def test_mock_ocr_provider_extract_and_normalize() -> None:
    provider = get_ocr_provider()

    raw = provider.extract_text(Path("sample.jpg"))
    normalized = provider.normalize_receipt(raw)

    assert raw.provider == "mock"
    assert raw.confidence > 0
    assert normalized.merchant == "Mock Mart"
    assert normalized.currency == "VND"
