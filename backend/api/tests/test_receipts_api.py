from __future__ import annotations

from pathlib import Path

from app.core.database import get_session
from app.core.security import create_access_token
from app.main import app
from app.models.entities import User
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def _reset_database() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def _cleanup_storage() -> None:
    storage_root = Path("data/receipts")
    if storage_root.exists():
        for file_path in storage_root.rglob("*"):
            if file_path.is_file():
                file_path.unlink()


def _override_session_factory() -> Session:
    with Session(engine) as session:
        yield session


def _seed_user() -> User:
    with Session(engine) as session:
        user = User(
            email="receipt@example.com",
            password_hash="hash",
            currency="VND",
            timezone="Asia/Ho_Chi_Minh",
            locale="vi-VN",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def test_upload_and_poll_receipt_status() -> None:
    _reset_database()
    _cleanup_storage()
    user = _seed_user()

    if user.id is None:
        raise AssertionError("Seeded user id is required")

    token = create_access_token(user_id=user.id, email=user.email)
    app.dependency_overrides[get_session] = _override_session_factory

    with TestClient(app) as client:
        client.cookies.set("pfa_session", token)

        upload = client.post(
            "/api/v1/receipts/upload",
            files={"file": ("sample.jpg", b"jpeg-binary", "image/jpeg")},
        )
        assert upload.status_code == 201
        upload_payload = upload.json()
        receipt_id = upload_payload["receipt_id"]
        assert upload_payload["status"] == "uploaded"

        receipt_status = client.get(f"/api/v1/receipts/{receipt_id}")
        assert receipt_status.status_code == 200
        assert receipt_status.json()["status"] in {"uploaded", "processing", "ready", "failed"}

        ocr_result = client.get(f"/api/v1/receipts/{receipt_id}/ocr-result")
        assert ocr_result.status_code == 404

    app.dependency_overrides.clear()
