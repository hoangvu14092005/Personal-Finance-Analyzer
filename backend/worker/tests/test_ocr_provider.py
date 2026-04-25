from __future__ import annotations

from ocr_provider import get_ocr_provider


def test_mock_ocr_provider_extract_and_normalize() -> None:
    provider = get_ocr_provider()

    raw = provider.extract_text(b"fake-jpeg-bytes", source_hint="sample.jpg")
    normalized = provider.normalize_receipt(raw)

    assert raw.provider == "mock"
    assert raw.confidence > 0
    assert "sample.jpg" in raw.raw_text
    assert normalized.merchant == "Mock Mart"
    assert normalized.currency == "VND"


def test_mock_ocr_provider_without_source_hint_uses_byte_count() -> None:
    provider = get_ocr_provider()
    raw = provider.extract_text(b"abcdef")
    assert "6 bytes" in raw.raw_text
