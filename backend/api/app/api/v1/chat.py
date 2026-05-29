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
from sqlalchemy import or_
from sqlmodel import Session, col, delete, select

from app.core.config import get_settings
from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import ChatConversation, ChatMessage, User
from app.schemas.chat import (
    ChatConversationCreate,
    ChatConversationListResponse,
    ChatConversationMessagesResponse,
    ChatConversationResponse,
    ChatHistoryResponse,
    ChatMessageItem,
    ChatMessageRequest,
)
from app.services.chat.conversations import (
    ChatConversationNotFoundError,
    ConversationSummary,
    create_conversation,
    delete_conversation_for_user,
    get_conversation_for_user,
    get_or_create_default_conversation,
    list_conversations_for_user,
)
from app.services.chat.llm_client import OpenAICompatClient
from app.services.chat.orchestrator import run_chat_turn
from app.services.chat.safety import RateLimitExceeded, check_rate_limit

router = APIRouter(prefix="/chat", tags=["chat"])


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return current_user.id


def _conversation_response(
    conversation: ChatConversation,
    *,
    message_count: int = 0,
    last_message_at: object | None = None,
) -> ChatConversationResponse:
    if conversation.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Conversation id missing",
        )
    return ChatConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count,
        last_message_at=last_message_at,  # type: ignore[arg-type]
    )


def _summary_response(summary: ConversationSummary) -> ChatConversationResponse:
    return _conversation_response(
        summary.conversation,
        message_count=summary.message_count,
        last_message_at=summary.last_message_at,
    )


def _message_item(msg: ChatMessage) -> ChatMessageItem:
    return ChatMessageItem(
        id=msg.id or 0,
        conversation_id=msg.conversation_id,
        role=msg.role,  # type: ignore[arg-type]
        content=msg.content,
        tool_calls=(json.loads(msg.tool_calls_json) if msg.tool_calls_json else None),
        tool_name=msg.tool_name,
        created_at=msg.created_at,
    )


def _load_visible_messages(
    session: Session,
    *,
    user_id: int,
    conversation_id: int | None = None,
    limit: int = 50,
    before_id: int | None = None,
) -> tuple[list[ChatMessage], bool, int | None]:
    query = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .where(ChatMessage.role != "tool")
    )
    if conversation_id is not None:
        query = query.where(ChatMessage.conversation_id == conversation_id)
    else:
        active_conversation_ids = select(ChatConversation.id).where(
            ChatConversation.user_id == user_id,
            ChatConversation.deleted_at.is_(None),  # type: ignore[union-attr]
        )
        query = query.where(
            or_(
                ChatMessage.conversation_id.is_(None),  # type: ignore[union-attr]
                col(ChatMessage.conversation_id).in_(active_conversation_ids),
            ),
        )
    if before_id is not None:
        query = query.where(col(ChatMessage.id) < before_id)

    rows = list(session.exec(query.order_by(col(ChatMessage.id).desc()).limit(limit + 1)).all())
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    rows.reverse()
    next_before = rows[0].id if has_more and rows else None
    return rows, has_more, next_before


def _resolve_conversation(
    session: Session,
    *,
    user_id: int,
    conversation_id: int | None,
) -> ChatConversation:
    if conversation_id is None:
        return get_or_create_default_conversation(session, user_id=user_id)
    try:
        return get_conversation_for_user(
            session,
            conversation_id=conversation_id,
            user_id=user_id,
        )
    except ChatConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        ) from exc


async def _stream_chat_response(
    *,
    payload: ChatMessageRequest,
    conversation_id: int,
    user_id: int,
    session: Session,
) -> StreamingResponse:
    # Rate limit
    try:
        settings = get_settings()
        check_rate_limit(user_id, settings.chat_rate_limit_per_minute)
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
                session,
                llm,
                user_id,
                payload.content,
                conversation_id=conversation_id,
            ):
                yield (
                    f"event: {event.event_type}\n"
                    f"data: {json.dumps(event.data, ensure_ascii=False)}\n\n"
                )
        except Exception:
            yield 'event: error\ndata: {"message": "Internal server error"}\n\n'
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


@router.post("/message")
async def send_message(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """Gửi message và nhận SSE stream response từ chatbot."""
    user_id = _require_user_id(current_user)
    conversation = _resolve_conversation(
        session,
        user_id=user_id,
        conversation_id=payload.conversation_id,
    )
    return await _stream_chat_response(
        payload=payload,
        conversation_id=conversation.id or 0,
        user_id=user_id,
        session=session,
    )


@router.get("/conversations", response_model=ChatConversationListResponse)
def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    before_id: int | None = Query(None, description="Cursor: conversations before this ID"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatConversationListResponse:
    user_id = _require_user_id(current_user)
    summaries, has_more, next_before = list_conversations_for_user(
        session,
        user_id=user_id,
        limit=limit,
        before_id=before_id,
    )
    return ChatConversationListResponse(
        items=[_summary_response(summary) for summary in summaries],
        has_more=has_more,
        next_before_id=next_before,
    )


@router.post(
    "/conversations",
    response_model=ChatConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation_endpoint(
    payload: ChatConversationCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatConversationResponse:
    user_id = _require_user_id(current_user)
    conversation = create_conversation(session, user_id=user_id, title=payload.title)
    return _conversation_response(conversation)


@router.post("/conversations/{conversation_id}/messages")
async def send_conversation_message(
    conversation_id: int,
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    user_id = _require_user_id(current_user)
    conversation = _resolve_conversation(
        session,
        user_id=user_id,
        conversation_id=conversation_id,
    )
    return await _stream_chat_response(
        payload=payload,
        conversation_id=conversation.id or conversation_id,
        user_id=user_id,
        session=session,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ChatConversationMessagesResponse,
)
def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=200),
    before_id: int | None = Query(None, description="Cursor: messages before this ID"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatConversationMessagesResponse:
    user_id = _require_user_id(current_user)
    conversation = _resolve_conversation(
        session,
        user_id=user_id,
        conversation_id=conversation_id,
    )
    rows, has_more, next_before = _load_visible_messages(
        session,
        user_id=user_id,
        conversation_id=conversation.id,
        limit=limit,
        before_id=before_id,
    )
    return ChatConversationMessagesResponse(
        conversation=_conversation_response(conversation, message_count=len(rows)),
        items=[_message_item(msg) for msg in rows],
        has_more=has_more,
        next_before_id=next_before,
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    user_id = _require_user_id(current_user)
    try:
        delete_conversation_for_user(session, conversation_id=conversation_id, user_id=user_id)
    except ChatConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/history", response_model=ChatHistoryResponse)
def get_history(
    limit: int = Query(50, ge=1, le=200),
    before_id: int | None = Query(None, description="Cursor: messages before this ID"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatHistoryResponse:
    """Lấy lịch sử chat, cursor-based pagination (newest first)."""
    user_id = _require_user_id(current_user)
    rows, has_more, next_before = _load_visible_messages(
        session,
        user_id=user_id,
        limit=limit,
        before_id=before_id,
    )
    return ChatHistoryResponse(
        items=[_message_item(msg) for msg in rows],
        has_more=has_more,
        next_before_id=next_before,
    )


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    """Xóa toàn bộ lịch sử chat của user."""
    user_id = _require_user_id(current_user)

    session.exec(
        delete(ChatMessage).where(ChatMessage.user_id == user_id),  # type: ignore[arg-type]
    )
    session.exec(
        delete(ChatConversation).where(ChatConversation.user_id == user_id),  # type: ignore[arg-type]
    )
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
