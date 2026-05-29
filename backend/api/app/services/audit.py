"""Audit event persistence helpers."""
from __future__ import annotations

import json
from collections.abc import Mapping

from sqlmodel import Session, select

from app.models.entities import AuditLog


def _metadata_json(metadata: Mapping[str, object] | None) -> str:
    if not metadata:
        return "{}"
    normalized = {str(key): str(value) for key, value in metadata.items() if value is not None}
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)


def parse_metadata(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): str(value) for key, value in parsed.items()}


def record_audit_event(
    session: Session,
    *,
    user_id: int,
    event: str,
    actor_user_id: int | None = None,
    target_type: str | None = None,
    target_id: str | int | None = None,
    metadata: Mapping[str, object] | None = None,
    commit: bool = False,
) -> AuditLog:
    audit = AuditLog(
        user_id=user_id,
        actor_user_id=actor_user_id or user_id,
        event=event,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        metadata_json=_metadata_json(metadata),
    )
    session.add(audit)
    if commit:
        session.commit()
        session.refresh(audit)
    return audit


def list_audit_events(session: Session, *, user_id: int, limit: int = 50) -> list[AuditLog]:
    bounded_limit = max(1, min(limit, 100))
    statement = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(bounded_limit)
    )
    return list(session.exec(statement).all())


__all__ = ["list_audit_events", "parse_metadata", "record_audit_event"]
