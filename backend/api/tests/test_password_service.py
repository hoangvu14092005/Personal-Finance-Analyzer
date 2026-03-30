from __future__ import annotations

from app.services.password_service import hash_password, verify_password


def test_hash_password_creates_non_plaintext_value() -> None:
    raw_password = "Finance123"

    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert hashed


def test_verify_password_returns_true_for_correct_password() -> None:
    raw_password = "Finance123"
    hashed = hash_password(raw_password)

    assert verify_password(raw_password, hashed) is True


def test_verify_password_returns_false_for_wrong_password() -> None:
    hashed = hash_password("Finance123")

    assert verify_password("WrongPassword123", hashed) is False
