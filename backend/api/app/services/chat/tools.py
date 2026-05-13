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
    get_budget_status,
    get_recent_transactions,
    get_spending_by_day,
    get_top_merchants,
    query_spending_summary,
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
