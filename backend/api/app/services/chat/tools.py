"""Tool registry cho LLM function calling (Phase 6.4).

Maps query functions → OpenAI tool definitions.
`execute_tool` enforces user_id server-side (defense in depth).
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlmodel import Session

from app.core.logging import get_logger
from app.services.chat.queries import (
    compare_periods,
    diagnose_spending_change,
    forecast_month_spending,
    get_budget_status,
    get_product_breakdown,
    get_recent_transactions,
    get_spending_by_day,
    get_tax_summary,
    get_top_merchants,
    lookup_transaction_receipts,
    query_spending_summary,
    search_receipts,
    search_transactions,
)
from app.services.chat.rag_queries import (
    search_receipt_text,
    semantic_search_transactions,
)

logger = get_logger("api.chat.tools")


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Một tool cho LLM."""

    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: Callable[..., dict[str, Any]]


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "query_spending_summary": ToolDefinition(
        name="query_spending_summary",
        description=(
            "Get total spending for a time period, optionally filtered"
            " by category name. Returns total, count, top categories."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "date_range": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                    "description": "Time period preset",
                },
                "category_name": {
                    "type": "string",
                    "description": "Category name to filter (optional, e.g. 'Ăn uống')",
                },
            },
            "required": ["date_range"],
        },
        handler=query_spending_summary,
    ),
    "search_transactions": ToolDefinition(
        name="search_transactions",
        description=(
            "Search transactions by merchant name, date range,"
            " amount range, or category. Returns matching list."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "merchant": {
                    "type": "string",
                    "description": "Merchant name to search (partial match)",
                },
                "date_range": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                    "description": "Time period preset",
                },
                "amount_min": {
                    "type": "number",
                    "description": "Minimum amount filter",
                },
                "amount_max": {
                    "type": "number",
                    "description": "Maximum amount filter",
                },
                "category_name": {
                    "type": "string",
                    "description": "Category name filter",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 20, max 50)",
                },
            },
            "required": [],
        },
        handler=search_transactions,
    ),
    "search_receipts": ToolDefinition(
        name="search_receipts",
        description=(
            "Search receipt/invoice evidence uploaded by the user. Use for questions"
            " about receipts, invoices, documents, upload date, receipt date, OCR"
            " status, or whether a receipt has become a transaction. Do not use this"
            " tool to calculate official spending totals."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "receipt_date": {
                    "type": "string",
                    "description": "Date printed on the receipt/invoice in YYYY-MM-DD format",
                },
                "created_date": {
                    "type": "string",
                    "description": "Upload date in YYYY-MM-DD format",
                },
                "merchant": {
                    "type": "string",
                    "description": "Merchant/seller name to search (partial match)",
                },
                "status": {
                    "type": "string",
                    "description": (
                        "Receipt pipeline status, e.g. uploaded, processing, ready, failed"
                    ),
                },
                "ocr_status": {
                    "type": "string",
                    "description": "OCR status, e.g. pending, processing, ready, failed",
                },
                "has_transaction": {
                    "type": "boolean",
                    "description": "Filter receipts that have or do not have a linked transaction",
                },
                "has_invoice": {
                    "type": "boolean",
                    "description": "Filter structured e-invoices/VAT invoices",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10, max 50)",
                },
            },
            "required": [],
        },
        handler=search_receipts,
    ),
    "lookup_transaction_receipts": ToolDefinition(
        name="lookup_transaction_receipts",
        description=(
            "Search transactions and report whether each transaction has linked receipt"
            " evidence. Use when the user asks if a transaction has a receipt/invoice."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "merchant": {
                    "type": "string",
                    "description": "Merchant name to search (partial match)",
                },
                "transaction_date": {
                    "type": "string",
                    "description": "Exact transaction date in YYYY-MM-DD format",
                },
                "date_range": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                    "description": "Time period preset based on official transaction date",
                },
                "has_receipt": {
                    "type": "boolean",
                    "description": "Filter transactions with or without linked receipt evidence",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10, max 50)",
                },
            },
            "required": [],
        },
        handler=lookup_transaction_receipts,
    ),
    "get_budget_status": ToolDefinition(
        name="get_budget_status",
        description=(
            "Get budget usage status for a month. Shows each"
            " budget's spent vs limit and whether exceeded."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "period_month": {
                    "type": "string",
                    "description": "Month in YYYY-MM format (default: current month)",
                },
            },
            "required": [],
        },
        handler=get_budget_status,
    ),
    "compare_periods": ToolDefinition(
        name="compare_periods",
        description=(
            "Compare spending between two time periods."
            " Returns totals and delta percentage."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "period_a": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                    "description": "First period to compare",
                },
                "period_b": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                    "description": "Second period to compare",
                },
            },
            "required": ["period_a", "period_b"],
        },
        handler=compare_periods,
    ),
    "get_top_merchants": ToolDefinition(
        name="get_top_merchants",
        description="Get top merchants ranked by total spending in a time period.",
        parameters_schema={
            "type": "object",
            "properties": {
                "date_range": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                    "description": "Time period preset",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of top merchants (default 10, max 20)",
                },
            },
            "required": ["date_range"],
        },
        handler=get_top_merchants,
    ),
    "get_spending_by_day": ToolDefinition(
        name="get_spending_by_day",
        description="Get daily spending breakdown for a time period. Shows amount per day.",
        parameters_schema={
            "type": "object",
            "properties": {
                "date_range": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                    "description": "Time period preset",
                },
            },
            "required": ["date_range"],
        },
        handler=get_spending_by_day,
    ),
    "get_recent_transactions": ToolDefinition(
        name="get_recent_transactions",
        description=(
            "Get the most recent transactions."
            " Returns latest N transactions ordered by date."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of transactions (default 10, max 50)",
                },
            },
            "required": [],
        },
        handler=get_recent_transactions,
    ),
    "search_receipt_text": ToolDefinition(
        name="search_receipt_text",
        description=(
            "Search detailed content within receipt OCR text."
            " Use when user asks about specific items, services, or line items"
            " inside a receipt (e.g., 'what did I buy at Grab yesterday?')."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search in receipt text (e.g., 'coffee', 'trà sữa')",
                },
                "date_range": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                    "description": "Filter by time period",
                },
                "merchant": {
                    "type": "string",
                    "description": "Filter by merchant name (partial match)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5, max 10)",
                },
            },
            "required": ["query"],
        },
        handler=search_receipt_text,
    ),
    "semantic_search_transactions": ToolDefinition(
        name="semantic_search_transactions",
        description=(
            "Search transactions semantically by meaning. Use when keywords"
            " are abstract (skincare, travel, pets, medical) that may not"
            " match exact DB values. Uses vector similarity."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Semantic query (e.g., 'skincare items', 'travel expenses')",
                },
                "date_range": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                },
                "amount_min": {"type": "number"},
                "amount_max": {"type": "number"},
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10, max 20)",
                },
            },
            "required": ["query"],
        },
        handler=semantic_search_transactions,
    ),
    "get_product_breakdown": ToolDefinition(
        name="get_product_breakdown",
        description=(
            "Get top products/items bought, aggregated from confirmed receipt"
            " line items. Use when user asks which products/items they spent on"
            " (e.g., 'tôi mua món gì nhiều nhất', 'chi cho cà phê bao nhiêu')."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "date_range": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                    "description": "Time period preset",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max products (default 10, max 50)",
                },
            },
            "required": [],
        },
        handler=get_product_breakdown,
    ),
    "get_tax_summary": ToolDefinition(
        name="get_tax_summary",
        description=(
            "Get total VAT/tax paid and top sellers (by tax id), from confirmed"
            " e-invoices. Use when user asks about VAT, thuế, hóa đơn đỏ, or"
            " spending grouped by seller tax id."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "date_range": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                    "description": "Time period preset",
                },
            },
            "required": [],
        },
        handler=get_tax_summary,
    ),
    "diagnose_spending_change": ToolDefinition(
        name="diagnose_spending_change",
        description=(
            "Explain WHY spending changed vs the previous period: which categories"
            " and merchants drove the change. Use for 'vì sao tháng này tôi tiêu"
            " nhiều hơn', 'cái gì làm chi tăng/giảm'."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "date_range": {
                    "type": "string",
                    "enum": ["7d", "30d", "this_month", "last_month"],
                    "description": "Period to diagnose (compared to its previous period)",
                },
            },
            "required": [],
        },
        handler=diagnose_spending_change,
    ),
    "forecast_month_spending": ToolDefinition(
        name="forecast_month_spending",
        description=(
            "Forecast end-of-month spending using current run-rate, and warn which"
            " budgets are projected to exceed. Use for 'cuối tháng tôi tiêu hết bao"
            " nhiêu', 'có vượt ngân sách không', 'dự báo chi tiêu'."
        ),
        parameters_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=forecast_month_spending,
    ),
}


def get_openai_tools() -> list[dict[str, Any]]:
    """Chuyển TOOL_REGISTRY sang OpenAI tools format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema,
            },
        }
        for t in TOOL_REGISTRY.values()
    ]


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o: object) -> Any:
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


def execute_tool(
    session: Session,
    name: str,
    user_id: int,
    args: dict[str, Any],
) -> str:
    """Execute tool handler với user_id enforced.

    Returns JSON string (tool result content cho LLM).
    Nếu tool không tồn tại hoặc lỗi → trả error JSON thay vì raise.
    """
    if name not in TOOL_REGISTRY:
        logger.warning("chat.tool_unknown name=%s", name)
        return json.dumps({"error": f"Unknown tool: {name}"})

    # Defense in depth: strip user_id từ args nếu LLM truyền
    safe_args = {k: v for k, v in args.items() if k != "user_id"}

    tool = TOOL_REGISTRY[name]
    try:
        result = tool.handler(session, user_id, **safe_args)
        return json.dumps(result, ensure_ascii=False, cls=_DecimalEncoder)
    except Exception as exc:
        logger.exception("chat.tool_error name=%s user_id=%d", name, user_id)
        return json.dumps({"error": f"Tool execution failed: {exc!s}"})


__all__ = ["TOOL_REGISTRY", "ToolDefinition", "execute_tool", "get_openai_tools"]
