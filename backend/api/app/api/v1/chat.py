"""Chat API endpoints — SSE streaming (Phase 6.7).

Endpoints:
- POST /api/v1/chat/message  : gửi message, nhận SSE stream response
- GET  /api/v1/chat/history  : lấy lịch sử chat (cursor pagination)
- DELETE /api/v1/chat/history : xóa toàn bộ lịch sử
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, col, delete, select

from app.core.config import get_settings
from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import ChatMessage, User
from app.schemas.chat import ChatHistoryResponse, ChatMessageItem, ChatMessageRequest
from app.services.chat.llm_client import OpenAICompatClient
from app.services.chat.orchestrator import run_chat_turn
from app.services.chat.safety import RateLimitExceeded, check_rate_limit

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message")
async def send_message(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """Gửi message và nhận SSE stream response từ chatbot."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    # Rate limit
    try:
        settings = get_settings()
        check_rate_limit(current_user.id, settings.chat_rate_limit_per_minute)
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Bạn gửi quá nhanh. Vui lòng đợi 1 phút.",
            headers={"Retry-After": "60"},
        ) from None

    settings = get_settings()
    llm = OpenAICompatClient(
        base_url=settings.chat_llm_base_url,
        api_key=settings.chat_llm_api_key,
        model=settings.chat_llm_model,
        timeout_seconds=settings.chat_llm_timeout_seconds,
    )

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in run_chat_turn(
                session, llm, current_user.id, payload.content,  # type: ignore[arg-type]
            ):
                yield (
                    f"event: {event.event_type}\n"
                    f"data: {json.dumps(event.data, ensure_ascii=False)}\n\n"
                )
        except Exception:
            yield (
                'event: error\n'
                'data: {"message": "Internal server error"}\n\n'
            )
        finally:
            await llm.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/history", response_model=ChatHistoryResponse)
def get_history(
    limit: int = Query(50, ge=1, le=200),
    before_id: int | None = Query(None, description="Cursor: messages before this ID"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatHistoryResponse:
    """Lấy lịch sử chat, cursor-based pagination (newest first)."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    query = (
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .where(ChatMessage.role != "tool")  # Hide tool messages from UI
    )

    if before_id is not None:
        query = query.where(col(ChatMessage.id) < before_id)

    query = query.order_by(col(ChatMessage.id).desc()).limit(limit + 1)
    rows = list(session.exec(query).all())

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    # Reverse to chronological order for frontend
    rows.reverse()

    items = [
        ChatMessageItem(
            id=msg.id or 0,
            role=msg.role,  # type: ignore[arg-type]
            content=msg.content,
            tool_calls=(
                json.loads(msg.tool_calls_json)
                if msg.tool_calls_json
                else None
            ),
            tool_name=msg.tool_name,
            created_at=msg.created_at,
        )
        for msg in rows
    ]

    next_before = rows[0].id if has_more and rows else None

    return ChatHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_id=next_before,
    )


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    """Xóa toàn bộ lịch sử chat của user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    session.exec(
        delete(ChatMessage).where(ChatMessage.user_id == current_user.id),  # type: ignore[arg-type]
    )
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
