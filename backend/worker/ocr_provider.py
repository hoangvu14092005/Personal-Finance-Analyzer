"""OCR provider abstraction (M5 refactor + Phase 7.5 real OCR).

M5: extract_text(content: bytes) thay vì extract_text(file_path: Path).
Phase 7.5: thêm `LLMVisionOCRProvider` dùng multimodal LLM (cx/gpt-5.5).

Providers:
- `MockOCRProvider`: fake data, dùng cho tests.
- `LLMVisionOCRProvider`: dùng LLM vision để OCR hóa đơn thật.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Protocol

import httpx

logger = logging.getLogger("worker.ocr")


@dataclass(frozen=True, slots=True)
class OCRRawResult:
    """Raw OCR output từ provider."""
    provider: str       # "mock" | "llm_vision"
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


# System prompts cho LLM Vision OCR
OCR_EXTRACT_PROMPT = """Extract ALL visible text from this receipt image.
Return the raw text exactly as it appears, line by line.
Do not add any commentary, formatting, or interpretation.
Just the text content from the image."""

OCR_NORMALIZE_PROMPT = """Parse the following receipt text and return STRICT JSON with these fields:
- merchant: the store/restaurant name
- transaction_date: in ISO format YYYY-MM-DD (if ambiguous, use the most likely date)
- total_amount: total amount as a number (no currency symbol, no thousand separators)
- currency: currency code (VND, USD, EUR, etc.)

If any field cannot be determined, use these defaults:
- merchant: "Unknown"
- transaction_date: today's date
- total_amount: 0
- currency: "VND"

Return ONLY the JSON object, no markdown fences, no commentary.

Receipt text:
"""


class LLMVisionOCRProvider:
    """OCR provider dùng multimodal LLM (Phase 7.5).

    Flow:
    1. extract_text: gửi ảnh base64 → LLM trả raw text.
    2. normalize_receipt: gửi raw text → LLM parse JSON structured.

    Dùng cùng endpoint với chat LLM (tiết kiệm infra).
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 120.0,
    ) -> None:
        if not api_key:
            raise ValueError("LLMVisionOCRProvider requires api_key")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout_seconds

    def _detect_mime(self, content: bytes, source_hint: str = "") -> str:
        """Detect MIME type từ magic bytes hoặc file extension."""
        if content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if content.startswith(b"\x89PNG"):
            return "image/png"
        if content.startswith(b"GIF8"):
            return "image/gif"
        if content.startswith(b"RIFF") and b"WEBP" in content[:12]:
            return "image/webp"
        # Fallback từ extension
        ext = os.path.splitext(source_hint.lower())[1] if source_hint else ""
        mime_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".gif": "image/gif",
            ".webp": "image/webp", ".pdf": "application/pdf",
        }
        return mime_map.get(ext, "image/jpeg")

    def _call_llm(self, messages: list[dict], max_tokens: int = 800) -> str:
        """Gọi LLM, return content string."""
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
            },
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"LLM returned {response.status_code}: {response.text[:200]}",
            )
        data = response.json()
        content = data["choices"][0]["message"].get("content", "")
        return content or ""

    def extract_text(self, content: bytes, source_hint: str = "") -> OCRRawResult:
        """Gửi ảnh → LLM → raw text."""
        mime = self._detect_mime(content, source_hint)
        b64 = base64.b64encode(content).decode()

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_EXTRACT_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }
        ]

        try:
            raw_text = self._call_llm(messages, max_tokens=1000)
        except Exception as exc:
            logger.exception("ocr.llm_vision_failed source=%s", source_hint)
            raise RuntimeError(f"LLM vision OCR failed: {exc}") from exc

        # Confidence heuristic: nếu LLM trả text dài → high confidence
        confidence = 0.9 if len(raw_text.strip()) > 20 else 0.5

        return OCRRawResult(
            provider="llm_vision",
            raw_text=raw_text.strip(),
            confidence=confidence,
        )

    def normalize_receipt(self, raw: OCRRawResult) -> OCRNormalizedReceipt:
        """Parse raw text → structured JSON qua LLM."""
        if not raw.raw_text.strip():
            return _default_normalized()

        messages = [
            {
                "role": "user",
                "content": OCR_NORMALIZE_PROMPT + raw.raw_text,
            }
        ]

        try:
            response_text = self._call_llm(messages, max_tokens=300)
        except Exception as exc:
            logger.exception("ocr.normalize_failed")
            logger.warning("Falling back to default normalized receipt: %s", exc)
            return _default_normalized()

        # Parse JSON (strip code fences nếu có)
        json_text = response_text.strip()
        if json_text.startswith("```"):
            # Strip markdown code fences
            json_text = re.sub(r"^```(?:json)?\s*", "", json_text)
            json_text = re.sub(r"\s*```$", "", json_text)

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            logger.warning(
                "ocr.normalize_json_decode_failed response=%s",
                response_text[:200],
            )
            return _default_normalized()

        return _parse_normalized(data)


def _default_normalized() -> OCRNormalizedReceipt:
    """Fallback khi LLM không parse được."""
    return OCRNormalizedReceipt(
        merchant="Unknown",
        transaction_date=date.today().isoformat(),
        total_amount=Decimal("0"),
        currency="VND",
    )


def _parse_normalized(data: dict) -> OCRNormalizedReceipt:
    """Parse dict từ LLM response thành dataclass, với defensive defaults."""
    merchant = str(data.get("merchant") or "Unknown").strip() or "Unknown"

    # Parse date
    date_str = str(data.get("transaction_date") or "").strip()
    try:
        parsed_date = date.fromisoformat(date_str).isoformat()
    except (ValueError, TypeError):
        parsed_date = date.today().isoformat()

    # Parse amount
    amount_raw = data.get("total_amount", 0)
    try:
        if isinstance(amount_raw, str):
            # Remove thousand separators
            amount_raw = amount_raw.replace(",", "").replace(".", "").replace(" ", "")
        total_amount = Decimal(str(amount_raw))
    except (ValueError, InvalidOperation):
        total_amount = Decimal("0")

    currency = str(data.get("currency") or "VND").strip().upper() or "VND"

    return OCRNormalizedReceipt(
        merchant=merchant[:255],
        transaction_date=parsed_date,
        total_amount=total_amount,
        currency=currency[:10],
    )


def get_ocr_provider() -> OCRProvider:
    """Factory function: trả OCR provider dựa trên env config.

    - OCR_PROVIDER=mock (default): MockOCRProvider
    - OCR_PROVIDER=llm_vision: LLMVisionOCRProvider (cần CHAT_LLM_*)
    """
    provider = os.getenv("OCR_PROVIDER", "mock").lower().strip()

    if provider == "llm_vision":
        base_url = os.getenv("CHAT_LLM_BASE_URL", "").strip()
        api_key = os.getenv("CHAT_LLM_API_KEY", "").strip()
        model = os.getenv("CHAT_LLM_MODEL", "").strip()
        if not (base_url and api_key and model):
            logger.warning(
                "OCR_PROVIDER=llm_vision nhưng thiếu CHAT_LLM_*; fallback sang mock",
            )
            return MockOCRProvider()
        return LLMVisionOCRProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
        )

    return MockOCRProvider()
