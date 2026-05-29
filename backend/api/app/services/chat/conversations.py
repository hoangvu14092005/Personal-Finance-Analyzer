"""Conversation service for assistant chat threads."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlmodel import Session, col, func, select

from app.models.entities import ChatConversation, ChatMessage


class ChatConversationNotFoundError(Exception):
    """Conversation does not exist or is not owned by user."""


@dataclass(frozen=True, slots=True)
class ConversationSummary:
    conversation: ChatConversation
    message_count: int
    last_message_at: datetime | None


def create_conversation(
    session: Session,
    *,
    user_id: int,
    title: str | None = None,
) -> ChatConversation:
    conversation = ChatConversation(
        user_id=user_id,
        title=(title.strip() if title and title.strip() else None),
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def get_conversation_for_user(
    session: Session,
    *,
    conversation_id: int,
    user_id: int,
) -> ChatConversation:
    conversation = session.get(ChatConversation, conversation_id)
    if (
        conversation is None
        or conversation.user_id != user_id
        or conversation.deleted_at is not None
    ):
        raise ChatConversationNotFoundError("Conversation not found")
    return conversation


def get_or_create_default_conversation(
    session: Session,
    *,
    user_id: int,
) -> ChatConversation:
    conversation = session.exec(
        select(ChatConversation)
        .where(ChatConversation.user_id == user_id)
        .where(ChatConversation.deleted_at.is_(None))  # type: ignore[union-attr]
        .order_by(col(ChatConversation.updated_at).desc(), col(ChatConversation.id).desc()),
    ).first()
    if conversation is not None:
        return conversation
    return create_conversation(session, user_id=user_id, title="Cuộc trò chuyện mới")


def list_conversations_for_user(
    session: Session,
    *,
    user_id: int,
    limit: int = 50,
    before_id: int | None = None,
) -> tuple[list[ConversationSummary], bool, int | None]:
    statement = (
        select(ChatConversation)
        .where(ChatConversation.user_id == user_id)
        .where(ChatConversation.deleted_at.is_(None))  # type: ignore[union-attr]
    )
    if before_id is not None:
        statement = statement.where(col(ChatConversation.id) < before_id)

    rows = list(
        session.exec(
            statement.order_by(
                col(ChatConversation.updated_at).desc(),
                col(ChatConversation.id).desc(),
            ).limit(limit + 1),
        ).all(),
    )
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    conversation_ids = [row.id for row in rows if row.id is not None]
    counts: dict[int, int] = {}
    last_dates: dict[int, datetime | None] = {}
    if conversation_ids:
        aggregate_rows = session.exec(
            select(
                ChatMessage.conversation_id,
                func.count(ChatMessage.id),
                func.max(ChatMessage.created_at),
            )
            .where(col(ChatMessage.conversation_id).in_(conversation_ids))
            .group_by(ChatMessage.conversation_id),
        ).all()
        for conversation_id, count, last_at in aggregate_rows:
            if conversation_id is not None:
                counts[int(conversation_id)] = int(count or 0)
                last_dates[int(conversation_id)] = last_at

    summaries = [
        ConversationSummary(
            conversation=row,
            message_count=counts.get(row.id or -1, 0),
            last_message_at=last_dates.get(row.id or -1),
        )
        for row in rows
    ]
    next_before = rows[-1].id if has_more and rows else None
    return summaries, has_more, next_before


def touch_conversation(
    session: Session,
    conversation: ChatConversation,
    *,
    title_hint: str | None = None,
) -> None:
    if conversation.title is None and title_hint:
        conversation.title = title_hint.strip()[:80] or None
    conversation.updated_at = datetime.now(tz=UTC)
    session.add(conversation)


def delete_conversation_for_user(
    session: Session,
    *,
    conversation_id: int,
    user_id: int,
) -> None:
    conversation = get_conversation_for_user(
        session,
        conversation_id=conversation_id,
        user_id=user_id,
    )
    now = datetime.now(tz=UTC)
    conversation.deleted_at = now
    conversation.updated_at = now
    session.add(conversation)
    session.commit()


__all__ = [
    "ChatConversationNotFoundError",
    "ConversationSummary",
    "create_conversation",
    "delete_conversation_for_user",
    "get_conversation_for_user",
    "get_or_create_default_conversation",
    "list_conversations_for_user",
    "touch_conversation",
]
