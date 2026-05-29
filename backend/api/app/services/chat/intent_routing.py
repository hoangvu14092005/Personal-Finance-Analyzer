"""Deterministic intent hints for finance assistant tool routing.

The LLM still decides final arguments, but these hints keep core domain routing
stable: money questions read transactions; document questions read receipts.
"""
from __future__ import annotations

from datetime import date
from enum import StrEnum
from unicodedata import category, normalize


class AssistantIntent(StrEnum):
    SPENDING_SUMMARY = "spending_summary"
    RECEIPT_LOOKUP = "receipt_lookup"
    TRANSACTION_RECEIPT_LOOKUP = "transaction_receipt_lookup"
    GENERAL_OR_LLM = "general_or_llm"


def _fold_text(value: str) -> str:
    decomposed = normalize("NFD", value.lower())
    folded = "".join(ch for ch in decomposed if category(ch) != "Mn")
    return folded.replace("đ", "d")


def classify_assistant_intent(message: str) -> AssistantIntent:
    """Classify high-level assistant intent using conservative keyword rules."""
    text = _fold_text(message)

    receipt_terms = (
        "hoa don",
        "chung tu",
        "receipt",
        "invoice",
        "vat",
        "ocr",
        "anh goc",
        "file",
        "upload",
        "tai len",
    )
    transaction_terms = ("giao dich", "transaction", "khoan chi", "dong tien")
    money_terms = (
        "tieu bao nhieu",
        "chi tieu",
        "tong tien",
        "tong chi",
        "ngan sach",
        "budget",
        "dashboard",
        "analytics",
        "vuot ngan sach",
        "top merchant",
        "bao cao",
    )

    has_receipt_term = any(term in text for term in receipt_terms)
    has_transaction_term = any(term in text for term in transaction_terms)

    if has_receipt_term and has_transaction_term:
        return AssistantIntent.TRANSACTION_RECEIPT_LOOKUP
    if has_receipt_term:
        return AssistantIntent.RECEIPT_LOOKUP
    if any(term in text for term in money_terms):
        return AssistantIntent.SPENDING_SUMMARY
    return AssistantIntent.GENERAL_OR_LLM


def build_intent_hint(message: str, *, today: date | None = None) -> str | None:
    """Build a compact system hint for the current user message."""
    intent = classify_assistant_intent(message)
    today_value = today or date.today()

    if intent == AssistantIntent.SPENDING_SUMMARY:
        return (
            f"Intent routing hint: {intent.value}. Use transaction SQL tools only "
            "for official totals, budgets, rankings, and analytics. Current date: "
            f"{today_value.isoformat()}."
        )
    if intent == AssistantIntent.RECEIPT_LOOKUP:
        return (
            f"Intent routing hint: {intent.value}. Prefer search_receipts for receipt, "
            "invoice, upload, OCR, or evidence lookup. Use receipt_date for the date "
            "printed on the document and created_date for upload date. Current date: "
            f"{today_value.isoformat()}."
        )
    if intent == AssistantIntent.TRANSACTION_RECEIPT_LOOKUP:
        return (
            f"Intent routing hint: {intent.value}. Prefer lookup_transaction_receipts "
            "when asking whether an official transaction has linked receipt/invoice "
            "evidence. Current date: "
            f"{today_value.isoformat()}."
        )
    return None


__all__ = ["AssistantIntent", "build_intent_hint", "classify_assistant_intent"]
