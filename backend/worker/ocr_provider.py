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
class OCRLineItem:
    """Single line item from receipt."""
    item_name: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal


@dataclass(frozen=True, slots=True)
class OCRInvoiceLineItem:
    """Single line item from Vietnamese e-invoice."""
    item_name: str
    unit: str | None
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal | None  # None → worker calculates quantity * unit_price
    vat_rate: Decimal | None    # e.g. Decimal("10") for 10%
    vat_amount: Decimal | None


@dataclass(frozen=True, slots=True)
class OCRInvoiceResult:
    """Full Vietnamese e-invoice extraction result."""
    # Metadata
    invoice_number: str | None
    template_symbol: str | None
    issue_date: str | None       # ISO "YYYY-MM-DD"
    tax_lookup_code: str | None
    currency: str

    # Seller
    seller_name: str | None
    seller_tax_id: str | None
    seller_address: str | None

    # Buyer
    buyer_name: str | None
    buyer_tax_id: str | None
    buyer_address: str | None
    payment_method: str | None

    # Line items
    line_items: list[OCRInvoiceLineItem]

    # Totals
    subtotal_before_tax: Decimal | None
    total_tax: Decimal | None
    grand_total: Decimal | None
    amount_in_words: str | None

    # Authentication
    digital_signature: str | None
    signing_date: str | None     # ISO "YYYY-MM-DD"
    lookup_link: str | None


@dataclass(frozen=True, slots=True)
class OCRNormalizedReceipt:
    """Normalized receipt data sau khi parse raw_text."""
    merchant: str
    transaction_date: str  # ISO format "YYYY-MM-DD"
    total_amount: Decimal
    currency: str
    line_items: list[OCRLineItem]  # Danh sách sản phẩm/dịch vụ


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

    def normalize_invoice(self, raw: OCRRawResult) -> OCRInvoiceResult:
        """Parse raw OCR text thành full Vietnamese e-invoice structure."""
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
            line_items=[
                OCRLineItem(
                    item_name="Cà phê sữa đá",
                    quantity=Decimal("2"),
                    unit_price=Decimal("25000"),
                    total_price=Decimal("50000"),
                ),
                OCRLineItem(
                    item_name="Bánh mì thịt",
                    quantity=Decimal("1"),
                    unit_price=Decimal("35000"),
                    total_price=Decimal("35000"),
                ),
                OCRLineItem(
                    item_name="Nước cam",
                    quantity=Decimal("2"),
                    unit_price=Decimal("20000"),
                    total_price=Decimal("40000"),
                ),
            ],
        )

    def normalize_invoice(self, raw: OCRRawResult) -> OCRInvoiceResult:  # noqa: ARG002
        return OCRInvoiceResult(
            invoice_number="0000123",
            template_symbol="1C24TAA",
            issue_date="2026-03-30",
            tax_lookup_code="ABC123XYZ",
            currency="VND",
            seller_name="Công ty TNHH Mock Mart",
            seller_tax_id="0123456789",
            seller_address="123 Nguyễn Huệ, Q.1, TP.HCM",
            buyer_name="Nguyễn Văn A",
            buyer_tax_id="9876543210",
            buyer_address="456 Lê Lợi, Q.3, TP.HCM",
            payment_method="Tiền mặt",
            line_items=[
                OCRInvoiceLineItem(
                    item_name="Cà phê sữa đá",
                    unit="ly",
                    quantity=Decimal("2"),
                    unit_price=Decimal("25000"),
                    line_total=Decimal("50000"),
                    vat_rate=Decimal("10"),
                    vat_amount=Decimal("5000"),
                ),
                OCRInvoiceLineItem(
                    item_name="Bánh mì thịt",
                    unit="cái",
                    quantity=Decimal("1"),
                    unit_price=Decimal("35000"),
                    line_total=Decimal("35000"),
                    vat_rate=Decimal("10"),
                    vat_amount=Decimal("3500"),
                ),
                OCRInvoiceLineItem(
                    item_name="Nước cam",
                    unit="ly",
                    quantity=Decimal("2"),
                    unit_price=Decimal("20000"),
                    line_total=Decimal("40000"),
                    vat_rate=Decimal("10"),
                    vat_amount=Decimal("4000"),
                ),
            ],
            subtotal_before_tax=Decimal("125000"),
            total_tax=Decimal("12500"),
            grand_total=Decimal("137500"),
            amount_in_words="Một trăm ba mươi bảy nghìn năm trăm đồng",
            digital_signature="Mock Digital Signature",
            signing_date="2026-03-30",
            lookup_link="https://tracuuhoadon.gdt.gov.vn/mock",
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
- line_items: array of items, each with:
  - item_name: product/service name
  - quantity: quantity as number (default 1 if not shown)
  - unit_price: price per unit as number
  - total_price: total for this line (quantity * unit_price)

If any field cannot be determined, use these defaults:
- merchant: "Unknown"
- transaction_date: today's date
- total_amount: 0
- currency: "VND"
- line_items: [] (empty array if no items found)

Return ONLY the JSON object, no markdown fences, no commentary.

Receipt text:
"""

OCR_INVOICE_NORMALIZE_PROMPT = """Parse the following Vietnamese e-invoice (hóa đơn điện tử) text and return STRICT JSON:
{
  "invoice_number": "string or null",
  "template_symbol": "string or null (ký hiệu mẫu số)",
  "issue_date": "YYYY-MM-DD or null",
  "tax_lookup_code": "string or null (mã tra cứu thuế)",
  "currency": "VND",
  "seller_name": "string or null",
  "seller_tax_id": "string or null (MST người bán)",
  "seller_address": "string or null",
  "buyer_name": "string or null",
  "buyer_tax_id": "string or null (MST người mua)",
  "buyer_address": "string or null",
  "payment_method": "string or null (hình thức thanh toán)",
  "line_items": [
    {
      "item_name": "string",
      "unit": "string or null (đơn vị tính)",
      "quantity": number,
      "unit_price": number,
      "line_total": number or null,
      "vat_rate": number or null (percentage, e.g. 10 for 10%),
      "vat_amount": number or null
    }
  ],
  "subtotal_before_tax": number or null (cộng tiền hàng),
  "total_tax": number or null (tổng tiền thuế),
  "grand_total": number or null (tổng tiền thanh toán),
  "amount_in_words": "string or null (số tiền bằng chữ)",
  "digital_signature": "string or null",
  "signing_date": "YYYY-MM-DD or null",
  "lookup_link": "string or null"
}

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

    def normalize_invoice(self, raw: OCRRawResult) -> OCRInvoiceResult:
        """Parse raw text → full Vietnamese e-invoice structure via LLM."""
        if not raw.raw_text.strip():
            return _default_invoice_normalized()

        messages = [
            {
                "role": "user",
                "content": OCR_INVOICE_NORMALIZE_PROMPT + raw.raw_text,
            }
        ]

        try:
            response_text = self._call_llm(messages, max_tokens=800)
        except Exception as exc:
            logger.exception("ocr.normalize_invoice_failed")
            logger.warning("Falling back to default invoice result: %s", exc)
            return _default_invoice_normalized()

        # Parse JSON (strip code fences nếu có)
        json_text = response_text.strip()
        if json_text.startswith("```"):
            json_text = re.sub(r"^```(?:json)?\s*", "", json_text)
            json_text = re.sub(r"\s*```$", "", json_text)

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            logger.warning(
                "ocr.normalize_invoice_json_decode_failed response=%s",
                response_text[:200],
            )
            return _default_invoice_normalized()

        return _parse_invoice_normalized(data)


def _default_normalized() -> OCRNormalizedReceipt:
    """Fallback khi LLM không parse được."""
    return OCRNormalizedReceipt(
        merchant="Unknown",
        transaction_date=date.today().isoformat(),
        total_amount=Decimal("0"),
        currency="VND",
        line_items=[],
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

    # Parse line items
    line_items = []
    items_raw = data.get("line_items", [])
    if isinstance(items_raw, list):
        for idx, item_data in enumerate(items_raw):
            if not isinstance(item_data, dict):
                continue
            try:
                item_name = str(item_data.get("item_name", f"Item {idx+1}")).strip()
                
                # Parse quantity
                qty_raw = item_data.get("quantity", 1)
                if isinstance(qty_raw, str):
                    qty_raw = qty_raw.replace(",", "").replace(" ", "")
                quantity = Decimal(str(qty_raw))
                
                # Parse unit_price
                unit_raw = item_data.get("unit_price", 0)
                if isinstance(unit_raw, str):
                    unit_raw = unit_raw.replace(",", "").replace(" ", "")
                unit_price = Decimal(str(unit_raw))
                
                # Parse total_price
                total_raw = item_data.get("total_price", 0)
                if isinstance(total_raw, str):
                    total_raw = total_raw.replace(",", "").replace(" ", "")
                total_price = Decimal(str(total_raw))
                
                # Validate: if total_price is 0, calculate from quantity * unit_price
                if total_price == 0 and quantity > 0 and unit_price > 0:
                    total_price = quantity * unit_price
                
                line_items.append(OCRLineItem(
                    item_name=item_name[:500],
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                ))
            except (ValueError, InvalidOperation, TypeError):
                # Skip invalid line items
                logger.warning("Skipping invalid line item at index %d: %s", idx, item_data)
                continue

    return OCRNormalizedReceipt(
        merchant=merchant[:255],
        transaction_date=parsed_date,
        total_amount=total_amount,
        currency=currency[:10],
        line_items=line_items,
    )


def _default_invoice_normalized() -> OCRInvoiceResult:
    """Fallback khi LLM không parse được invoice."""
    return OCRInvoiceResult(
        invoice_number=None,
        template_symbol=None,
        issue_date=None,
        tax_lookup_code=None,
        currency="VND",
        seller_name=None,
        seller_tax_id=None,
        seller_address=None,
        buyer_name=None,
        buyer_tax_id=None,
        buyer_address=None,
        payment_method=None,
        line_items=[],
        subtotal_before_tax=None,
        total_tax=None,
        grand_total=None,
        amount_in_words=None,
        digital_signature=None,
        signing_date=None,
        lookup_link=None,
    )


def _parse_invoice_normalized(data: dict) -> OCRInvoiceResult:
    """Parse dict từ LLM response thành OCRInvoiceResult, với defensive defaults."""

    def _str_or_none(val: object, max_len: int = 500) -> str | None:
        if val is None:
            return None
        s = str(val).strip()
        return s[:max_len] if s else None

    def _decimal_or_none(val: object) -> Decimal | None:
        if val is None:
            return None
        try:
            raw = str(val).replace(",", "").replace(" ", "")
            if not raw:
                return None
            return Decimal(raw)
        except (ValueError, InvalidOperation):
            return None

    def _date_str_or_none(val: object) -> str | None:
        if val is None:
            return None
        s = str(val).strip()
        if not s:
            return None
        try:
            date.fromisoformat(s)
            return s
        except (ValueError, TypeError):
            return None

    # Parse line items
    line_items: list[OCRInvoiceLineItem] = []
    items_raw = data.get("line_items", [])
    if isinstance(items_raw, list):
        for idx, item_data in enumerate(items_raw):
            if not isinstance(item_data, dict):
                continue
            try:
                item_name = str(item_data.get("item_name", f"Item {idx+1}")).strip()
                if not item_name:
                    item_name = f"Item {idx+1}"

                unit = _str_or_none(item_data.get("unit"), max_len=50)

                # Parse quantity
                qty_raw = item_data.get("quantity", 1)
                if isinstance(qty_raw, str):
                    qty_raw = qty_raw.replace(",", "").replace(" ", "")
                quantity = Decimal(str(qty_raw)) if qty_raw else Decimal("1")

                # Parse unit_price
                up_raw = item_data.get("unit_price", 0)
                if isinstance(up_raw, str):
                    up_raw = up_raw.replace(",", "").replace(" ", "")
                unit_price = Decimal(str(up_raw)) if up_raw else Decimal("0")

                # Parse line_total (nullable)
                line_total = _decimal_or_none(item_data.get("line_total"))

                # Parse VAT fields
                vat_rate = _decimal_or_none(item_data.get("vat_rate"))
                vat_amount = _decimal_or_none(item_data.get("vat_amount"))

                line_items.append(OCRInvoiceLineItem(
                    item_name=item_name[:500],
                    unit=unit,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    vat_rate=vat_rate,
                    vat_amount=vat_amount,
                ))
            except (ValueError, InvalidOperation, TypeError):
                logger.warning("Skipping invalid invoice line item at index %d: %s", idx, item_data)
                continue

    return OCRInvoiceResult(
        invoice_number=_str_or_none(data.get("invoice_number"), max_len=100),
        template_symbol=_str_or_none(data.get("template_symbol"), max_len=50),
        issue_date=_date_str_or_none(data.get("issue_date")),
        tax_lookup_code=_str_or_none(data.get("tax_lookup_code"), max_len=100),
        currency=str(data.get("currency") or "VND").strip().upper()[:10] or "VND",
        seller_name=_str_or_none(data.get("seller_name"), max_len=255),
        seller_tax_id=_str_or_none(data.get("seller_tax_id"), max_len=20),
        seller_address=_str_or_none(data.get("seller_address"), max_len=500),
        buyer_name=_str_or_none(data.get("buyer_name"), max_len=255),
        buyer_tax_id=_str_or_none(data.get("buyer_tax_id"), max_len=20),
        buyer_address=_str_or_none(data.get("buyer_address"), max_len=500),
        payment_method=_str_or_none(data.get("payment_method"), max_len=100),
        line_items=line_items,
        subtotal_before_tax=_decimal_or_none(data.get("subtotal_before_tax")),
        total_tax=_decimal_or_none(data.get("total_tax")),
        grand_total=_decimal_or_none(data.get("grand_total")),
        amount_in_words=_str_or_none(data.get("amount_in_words"), max_len=500),
        digital_signature=_str_or_none(data.get("digital_signature"), max_len=500),
        signing_date=_date_str_or_none(data.get("signing_date")),
        lookup_link=_str_or_none(data.get("lookup_link"), max_len=500),
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
