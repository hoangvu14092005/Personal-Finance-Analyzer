"""Tests cho suggest_category_for_merchant (G1 — LLM classification)."""
from __future__ import annotations

import app.services.category_suggestion as cs
from app.models.entities import Category, User, UserSettings
from sqlalchemy.engine import Engine
from sqlmodel import Session


def _seed_user(session: Session, email: str = "cat@example.com") -> int:
    user = User(email=email, password_hash="x")
    session.add(user)
    session.commit()
    session.refresh(user)
    assert user.id is not None
    return user.id


def _seed_system_category(session: Session, name: str) -> int:
    cat = Category(user_id=None, name=name, is_system=True)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    assert cat.id is not None
    return cat.id


def test_returns_none_when_no_categories(engine: Engine, monkeypatch) -> None:
    # Không seed category nào → LLM không được gọi, trả None.
    called = {"n": 0}

    def fake_classify(merchant, categories):  # noqa: ANN001
        called["n"] += 1
        return None

    monkeypatch.setattr(cs, "classify_merchant_category", fake_classify)
    with Session(engine) as session:
        user_id = _seed_user(session)
        result = cs.suggest_category_for_merchant(session, user_id, "Highlands Coffee")
        assert result is None
    assert called["n"] == 0  # không có category → không gọi LLM


def test_llm_classifies_and_caches(engine: Engine, monkeypatch) -> None:
    with Session(engine) as session:
        user_id = _seed_user(session)
        food_id = _seed_system_category(session, "Ăn uống")

        calls = {"n": 0}

        def fake_classify(merchant, categories):  # noqa: ANN001
            calls["n"] += 1
            assert any(cid == food_id for cid, _ in categories)
            return food_id

        monkeypatch.setattr(cs, "classify_merchant_category", fake_classify)

        # Lần 1: gọi LLM.
        result1 = cs.suggest_category_for_merchant(session, user_id, "Highlands Coffee")
        assert result1 == food_id
        assert calls["n"] == 1

        # Lần 2: cùng merchant → dùng alias đã cache, KHÔNG gọi lại LLM.
        result2 = cs.suggest_category_for_merchant(session, user_id, "Highlands Coffee")
        assert result2 == food_id
        assert calls["n"] == 1


def test_learned_mapping_wins_over_llm(engine: Engine, monkeypatch) -> None:
    with Session(engine) as session:
        user_id = _seed_user(session)
        _seed_system_category(session, "Ăn uống")
        shopping_id = _seed_system_category(session, "Mua sắm")

        def fake_classify(merchant, categories):  # noqa: ANN001
            raise AssertionError("LLM should not be called when mapping exists")

        monkeypatch.setattr(cs, "classify_merchant_category", fake_classify)

        cs.remember_user_merchant_category(session, user_id, "Highlands Coffee", shopping_id)
        result = cs.suggest_category_for_merchant(session, user_id, "Highlands Coffee")
        assert result == shopping_id


def test_ai_disabled_skips_llm(engine: Engine, monkeypatch) -> None:
    with Session(engine) as session:
        user_id = _seed_user(session)
        _seed_system_category(session, "Ăn uống")
        session.add(UserSettings(user_id=user_id, allow_ai_data_processing=False))
        session.commit()

        def fake_classify(merchant, categories):  # noqa: ANN001
            raise AssertionError("LLM must not be called when AI disabled")

        monkeypatch.setattr(cs, "classify_merchant_category", fake_classify)

        result = cs.suggest_category_for_merchant(session, user_id, "Highlands Coffee")
        assert result is None


def test_llm_returns_none_no_cache(engine: Engine, monkeypatch) -> None:
    with Session(engine) as session:
        user_id = _seed_user(session)
        _seed_system_category(session, "Ăn uống")

        def fake_classify(merchant, categories):  # noqa: ANN001
            return None

        monkeypatch.setattr(cs, "classify_merchant_category", fake_classify)

        result = cs.suggest_category_for_merchant(session, user_id, "Unknown Vendor")
        assert result is None
