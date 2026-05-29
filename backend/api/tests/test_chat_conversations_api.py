"""Tests for chat conversation APIs."""
from __future__ import annotations

from app.core.security import create_access_token
from app.models.entities import ChatConversation, ChatMessage, User
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session


def _seed_conversation(
    session: Session,
    *,
    user_id: int,
    title: str = "Budget chat",
) -> ChatConversation:
    conversation = ChatConversation(user_id=user_id, title=title)
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    assert conversation.id is not None
    return conversation


def _seed_message(
    session: Session,
    *,
    user_id: int,
    conversation_id: int,
    role: str,
    content: str | None,
) -> ChatMessage:
    message = ChatMessage(
        user_id=user_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


class TestConversationAuth:
    def test_list_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/chat/conversations")
        assert response.status_code == 401


class TestConversationCrud:
    def test_create_and_list_conversation(self, client: TestClient, auth_user: User) -> None:
        response = client.post(
            "/api/v1/chat/conversations",
            json={"title": "Phân tích tháng 5"},
        )
        assert response.status_code == 201
        created = response.json()
        assert created["title"] == "Phân tích tháng 5"
        assert created["message_count"] == 0

        list_response = client.get("/api/v1/chat/conversations")
        assert list_response.status_code == 200
        body = list_response.json()
        assert body["items"][0]["id"] == created["id"]
        assert body["items"][0]["title"] == "Phân tích tháng 5"
        assert body["has_more"] is False

    def test_delete_hides_conversation_and_messages_endpoint(
        self,
        client: TestClient,
        auth_user: User,
        db_session: Session,
    ) -> None:
        assert auth_user.id is not None
        conversation = _seed_conversation(db_session, user_id=auth_user.id)

        response = client.delete(f"/api/v1/chat/conversations/{conversation.id}")
        assert response.status_code == 204

        list_response = client.get("/api/v1/chat/conversations")
        assert list_response.status_code == 200
        assert list_response.json()["items"] == []

        messages_response = client.get(f"/api/v1/chat/conversations/{conversation.id}/messages")
        assert messages_response.status_code == 404

    def test_deleted_conversation_messages_hidden_from_legacy_history(
        self,
        client: TestClient,
        auth_user: User,
        db_session: Session,
    ) -> None:
        assert auth_user.id is not None
        conversation = _seed_conversation(db_session, user_id=auth_user.id)
        _seed_message(
            db_session,
            user_id=auth_user.id,
            conversation_id=conversation.id or 0,
            role="user",
            content="Ẩn sau khi xóa",
        )

        delete_response = client.delete(f"/api/v1/chat/conversations/{conversation.id}")
        assert delete_response.status_code == 204

        history_response = client.get("/api/v1/chat/history")
        assert history_response.status_code == 200
        assert history_response.json()["items"] == []


class TestConversationMessages:
    def test_messages_are_scoped_and_tool_messages_hidden(
        self,
        client: TestClient,
        auth_user: User,
        db_session: Session,
    ) -> None:
        assert auth_user.id is not None
        first = _seed_conversation(db_session, user_id=auth_user.id, title="First")
        second = _seed_conversation(db_session, user_id=auth_user.id, title="Second")
        _seed_message(
            db_session,
            user_id=auth_user.id,
            conversation_id=first.id or 0,
            role="user",
            content="Tôi tiêu bao nhiêu?",
        )
        _seed_message(
            db_session,
            user_id=auth_user.id,
            conversation_id=first.id or 0,
            role="tool",
            content='{"total_spend":"1000"}',
        )
        _seed_message(
            db_session,
            user_id=auth_user.id,
            conversation_id=first.id or 0,
            role="assistant",
            content="Bạn đã tiêu 1.000 VND.",
        )
        _seed_message(
            db_session,
            user_id=auth_user.id,
            conversation_id=second.id or 0,
            role="user",
            content="Hóa đơn đâu?",
        )

        response = client.get(f"/api/v1/chat/conversations/{first.id}/messages")

        assert response.status_code == 200
        body = response.json()
        assert body["conversation"]["id"] == first.id
        assert [item["role"] for item in body["items"]] == ["user", "assistant"]
        assert all(item["conversation_id"] == first.id for item in body["items"])
        assert "Hóa đơn đâu?" not in [item["content"] for item in body["items"]]

    def test_cross_user_conversation_returns_404(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        with Session(engine) as session:
            other = User(email="other-chat@example.com", password_hash="x")
            session.add(other)
            session.commit()
            session.refresh(other)
            assert other.id is not None
            conversation = _seed_conversation(session, user_id=other.id)

        response = client.get(f"/api/v1/chat/conversations/{conversation.id}/messages")
        assert response.status_code == 404

    def test_legacy_history_still_returns_visible_messages(
        self,
        client: TestClient,
        auth_user: User,
        db_session: Session,
    ) -> None:
        assert auth_user.id is not None
        conversation = _seed_conversation(db_session, user_id=auth_user.id)
        _seed_message(
            db_session,
            user_id=auth_user.id,
            conversation_id=conversation.id or 0,
            role="user",
            content="Legacy vẫn thấy",
        )

        response = client.get("/api/v1/chat/history")

        assert response.status_code == 200
        body = response.json()
        assert body["items"][0]["content"] == "Legacy vẫn thấy"
        assert body["items"][0]["conversation_id"] == conversation.id


class TestConversationIsolation:
    def test_list_only_current_user_conversations(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        with Session(engine) as session:
            mine = _seed_conversation(session, user_id=auth_user.id, title="Mine")
            mine_id = mine.id
            other = User(email="other-list@example.com", password_hash="x")
            session.add(other)
            session.commit()
            session.refresh(other)
            assert other.id is not None
            _seed_conversation(session, user_id=other.id, title="Other")

        response = client.get("/api/v1/chat/conversations")

        assert response.status_code == 200
        items = response.json()["items"]
        assert [item["id"] for item in items] == [mine_id]

    def test_other_user_can_access_their_own_conversation(
        self,
        engine: Engine,
        client: TestClient,
    ) -> None:
        with Session(engine) as session:
            other = User(email="owner@example.com", password_hash="x")
            session.add(other)
            session.commit()
            session.refresh(other)
            assert other.id is not None
            other_id = other.id
            other_email = other.email
            conversation = _seed_conversation(session, user_id=other.id, title="Owner")
            conversation_id = conversation.id

        token = create_access_token(user_id=other_id, email=other_email)
        client.cookies.set("pfa_session", token)
        response = client.get(f"/api/v1/chat/conversations/{conversation_id}/messages")

        assert response.status_code == 200
        assert response.json()["conversation"]["id"] == conversation_id
