"""Audit log APIs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import AuditLog, User
from app.schemas.audit import AuditLogItemResponse, AuditLogResponse
from app.services.audit import list_audit_events, parse_metadata

router = APIRouter(prefix="/audit-log", tags=["audit"])


def _audit_item_response(audit: AuditLog) -> AuditLogItemResponse:
    if audit.id is None:
        raise ValueError("Audit log id missing")
    return AuditLogItemResponse(
        id=str(audit.id),
        event=audit.event,
        occurred_at=audit.created_at,
        actor_user_id=audit.actor_user_id,
        target_type=audit.target_type,
        target_id=audit.target_id,
        metadata=parse_metadata(audit.metadata_json),
    )


@router.get("", response_model=AuditLogResponse)
def list_audit_log(
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AuditLogResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    items = list_audit_events(session, user_id=current_user.id, limit=limit)
    return AuditLogResponse(items=[_audit_item_response(item) for item in items])


__all__ = ["router"]
