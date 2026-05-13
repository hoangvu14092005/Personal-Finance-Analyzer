"""Chat orchestrator — multi-turn loop với tool calling (Phase 6.5).

Core function `run_chat_turn`: user message → (tool calls)* → assistant response.
Persist mọi message vào DB. Stream final text response.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal

from sqlmodel import Session, col, select

from app.core.logging import get_logger
from app.models.entities import ChatMessage
from app.services.chat.llm_client import LLMClientError, OpenAICompatClient
from app.services.chat.safety import apply_safety_filter
from app.services.chat.system_prompt import SYSTEM_PROMPT
from app.services.chat.tools import execute_tool, get_openai_tools

logger = get_logger("api.chat.orchestrator")

MAX_TOOL_ROUNDS = 5
MAX_HISTORY_MESSAGES = 40


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    """Event emitted during chat turn."""

    event_type: Literal["token", "tool_call", "done", "error"]
    data: dict[str, Any]


def _load_recent_history(
    session: Session,
    user_id: int,
    limit: int = MAX_HISTORY_MESSAGES,
) -> list[ChatMessage]:
    """Load N messages gần nhất của user, ordered ASC (oldest first)."""
    statement = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(col(ChatMessage.created_at).desc(), col(ChatMessage.id).desc())
        .limit(limit)
    )
    rows = list(session.exec(statement).all())
    rows.reverse()  # Oldest first for conversation order
    return rows


def _history_to_openai_format(history: list[ChatMessage]) -> list[dict[str, Any]]:
    """Convert ChatMessage rows → OpenAI messages format."""
    messages: list[dict[str, Any]] = []
    for msg in history:
        if msg.role == "user":
            messages.append({"role": "user", "content": msg.content or ""})
        elif msg.role == "assistant":
            entry: dict[str, Any] = {"role": "assistant"}
            if msg.tool_calls_json:
                entry["content"] = None
                entry["tool_calls"] = json.loads(msg.tool_calls_json)
            else:
                entry["content"] = msg.content or ""
            messages.append(entry)
        elif msg.role == "tool":
            messages.append({
                "role": "tool",
                "tool_call_id": msg.tool_call_id or "",
                "content": msg.content or "",
            })
    return messages


def _persist_message(
    session: Session,
    user_id: int,
    role: str,
    content: str | None = None,
    tool_calls_json: str | None = None,
    tool_call_id: str | None = None,
    tool_name: str | None = None,
) -> ChatMessage:
    """Persist a single chat message."""
    msg = ChatMessage(
        user_id=user_id,
        role=role,
        content=content,
        tool_calls_json=tool_calls_json,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


async def run_chat_turn(
    session: Session,
    llm: OpenAICompatClient,
    user_id: int,
    user_message: str,
) -> AsyncIterator[ChatStreamEvent]:
    """Thực hiện 1 turn: user message → (tool calls)* → streamed response.

    Yields ChatStreamEvent objects. Caller converts to SSE.
    """
    import time
    start = time.perf_counter()

    # 1. Load history
    history = _load_recent_history(session, user_id)

    # 2. Persist user message
    _persist_message(session, user_id, "user", content=user_message)

    # 3. Build messages array
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    messages.extend(_history_to_openai_format(history))
    messages.append({"role": "user", "content": user_message})

    # 4. Tool-calling loop
    tools = get_openai_tools()
    tool_calls_count = 0

    for round_num in range(MAX_TOOL_ROUNDS):
        try:
            response = await llm.chat(messages, tools=tools, stream=False)
        except LLMClientError as exc:
            logger.exception("chat.llm_error user_id=%d round=%d", user_id, round_num)
            _persist_message(
                session, user_id, "assistant",
                content="Xin lỗi, hệ thống đang bận. Vui lòng thử lại sau.",
            )
            yield ChatStreamEvent("error", {"message": str(exc)})
            return

        # response is dict (non-streaming call)
        assert isinstance(response, dict)
        choice = response["choices"][0]
        msg = choice["message"]

        if msg.get("tool_calls"):
            # Execute tools
            tool_calls = msg["tool_calls"]
            tool_calls_count += len(tool_calls)

            # Persist assistant message with tool_calls
            _persist_message(
                session, user_id, "assistant",
                tool_calls_json=json.dumps(tool_calls, ensure_ascii=False),
            )

            # Append to messages for next round
            messages.append(msg)

            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                yield ChatStreamEvent("tool_call", {"name": tool_name})

                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}

                # Execute with enforced user_id
                result_str = execute_tool(session, tool_name, user_id, args)

                # Persist tool result
                _persist_message(
                    session, user_id, "tool",
                    content=result_str,
                    tool_call_id=tc["id"],
                    tool_name=tool_name,
                )

                # Append to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_str,
                })

            continue  # Next round

        # Final text response — stream it
        content = msg.get("content", "") or ""
        content = apply_safety_filter(content)

        # For streaming: re-call LLM with stream=True for the final answer
        # But since we already have the content, just yield it in chunks
        # (simpler for MVP; real streaming would re-call)
        chunk_size = 20  # characters per chunk for simulated streaming
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            yield ChatStreamEvent("token", {"content": chunk})

        # Persist final assistant message
        _persist_message(session, user_id, "assistant", content=content)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "chat.turn_end user_id=%d rounds=%d tool_calls=%d "
            "duration_ms=%.1f",
            user_id, round_num + 1, tool_calls_count, elapsed_ms,
        )

        yield ChatStreamEvent("done", {})
        return

    # Hit max rounds
    _persist_message(
        session, user_id, "assistant",
        content="Xin lỗi, câu hỏi quá phức tạp. Hãy thử câu ngắn hơn.",
    )
    yield ChatStreamEvent("error", {"message": "Max tool rounds exceeded"})


__all__ = ["ChatStreamEvent", "run_chat_turn"]
