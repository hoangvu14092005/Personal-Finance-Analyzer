"""Core orchestrator (Phase 6.6 + 6.7).

Flow `generate_insight_for_user(session, provider, user_id, range_preset, ...)`:
1. Resolve `DateRange` từ preset (dùng `services.date_ranges`).
2. Compute analytics summary (dùng `services.analytics.compute_summary`).
3. Build `SummaryInput` (dùng `services.insights.summary.build_summary_input`).
4. Check eligibility — nếu fail → tạo fallback snapshot `insufficient_data`.
5. Fingerprint lookup cache → nếu hit (và không force) → return snapshot cũ.
6. Gọi provider.generate(summary) — nếu raise → tạo fallback `failed`.
7. Run safety checks → filter items vi phạm.
8. Persist `InsightSnapshot` với payload + metadata.
9. Return `InsightResponse` (hoặc snapshot dataclass cho caller).

Public API:
- `generate_insight_for_user`: sync, raise không bắt (caller handle).
- Future: TaskIQ wrapper `generate_insight_job` cho async với Ollama/Gemini.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date
from typing import cast

from sqlmodel import Session, col, select

from app.core.logging import get_logger
from app.models.entities import InsightSnapshot
from app.schemas.insights import (
    AlertItem,
    GenerateInsightRequest,
    InsightItem,
    InsightPayload,
    InsightStatus,
    RecommendationItem,
)
from app.services.analytics import compute_summary
from app.services.date_ranges import (
    DateRange,
    InvalidDateRangeError,
    RangePreset,
    previous_period,
    resolve_range,
)
from app.services.insights.eligibility import check_eligibility
from app.services.insights.providers.base import (
    InsightProvider,
    InsightProviderError,
)
from app.services.insights.safety import run_safety_checks
from app.services.insights.summary import build_summary_input

logger = get_logger("api.insights.generator")


@dataclass(frozen=True, slots=True)
class GenerateResult:
    """Kết quả orchestrator. Dùng trong API layer để build response."""

    snapshot: InsightSnapshot
    payload: InsightPayload
    range_: DateRange
    cached: bool
    fingerprint: str
    status: InsightStatus
    status_reason: str | None


def _empty_payload() -> InsightPayload:
    return InsightPayload()


def snapshot_to_payload(snapshot: InsightSnapshot) -> InsightPayload:
    """Deserialize `InsightSnapshot.*_json` (strings) → `InsightPayload`.

    Snapshot lưu 3 arrays ở 3 columns (initial schema từ Phase 0.7).
    Nếu JSON corrupt (không parse được) → return empty payload + log warn.
    """
    try:
        insights_raw = json.loads(snapshot.insights_json or "[]")
        recs_raw = json.loads(snapshot.recommendations_json or "[]")
        alerts_raw = json.loads(snapshot.alerts_json or "[]")
    except json.JSONDecodeError:
        logger.exception(
            "insights.snapshot_json_corrupt snapshot_id=%s", snapshot.id,
        )
        return _empty_payload()

    try:
        return InsightPayload(
            insights=[InsightItem.model_validate(x) for x in insights_raw],
            recommendations=[
                RecommendationItem.model_validate(x) for x in recs_raw
            ],
            alerts=[AlertItem.model_validate(x) for x in alerts_raw],
        )
    except Exception:  # pragma: no cover — defensive Pydantic validation.
        logger.exception(
            "insights.snapshot_payload_invalid snapshot_id=%s", snapshot.id,
        )
        return _empty_payload()


def _find_cached_snapshot(
    session: Session,
    user_id: int,
    fingerprint: str,
) -> InsightSnapshot | None:
    """Cache lookup: (user_id, fingerprint) → latest snapshot (nếu có).

    Cache hit chỉ cho `status=ready` — không cache fallback vì data có
    thể thay đổi (user thêm transactions → eligible lại).
    """
    statement = (
        select(InsightSnapshot)
        .where(InsightSnapshot.user_id == user_id)
        .where(InsightSnapshot.fingerprint == fingerprint)
        .where(InsightSnapshot.status == "ready")
        .order_by(col(InsightSnapshot.created_at).desc())
        .limit(1)
    )
    return session.exec(statement).first()


def _persist_snapshot(
    session: Session,
    *,
    user_id: int,
    range_preset: str,
    range_: DateRange,
    provider_name: str,
    fingerprint: str,
    payload: InsightPayload,
    status: str,
    status_reason: str | None,
) -> InsightSnapshot:
    """Insert snapshot mới. Dùng Pydantic `model_dump` → JSON string."""
    snapshot = InsightSnapshot(
        user_id=user_id,
        range_preset=range_preset,
        range_start=range_.start,
        range_end=range_.end,
        provider=provider_name,
        insights_json=json.dumps(
            [item.model_dump() for item in payload.insights],
            ensure_ascii=False,
        ),
        recommendations_json=json.dumps(
            [item.model_dump() for item in payload.recommendations],
            ensure_ascii=False,
        ),
        alerts_json=json.dumps(
            [item.model_dump() for item in payload.alerts],
            ensure_ascii=False,
        ),
        fingerprint=fingerprint,
        status=status,
        status_reason=status_reason,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def _resolve_ranges(
    preset: str,
    start_date: date | None,
    end_date: date | None,
) -> tuple[RangePreset, DateRange, DateRange]:
    """Parse preset → (enum, current_range, previous_range).

    Raise `InvalidDateRangeError` nếu preset/custom invalid. API layer
    map về 400 response.
    """
    try:
        enum = RangePreset(preset)
    except ValueError as exc:
        raise InvalidDateRangeError(
            f"Invalid range preset: {preset!r}",
        ) from exc
    current = resolve_range(enum, custom_start=start_date, custom_end=end_date)
    previous = previous_period(current, enum)
    return enum, current, previous


def generate_insight_for_user(
    session: Session,
    provider: InsightProvider,
    user_id: int,
    request: GenerateInsightRequest,
) -> GenerateResult:
    """Orchestrate pipeline sinh insight + cache + persist.

    Raise `InvalidDateRangeError` khi preset/custom invalid (API → 400).
    Các lỗi khác (provider, safety) → fallback snapshot, KHÔNG raise.

    Args:
        session: SQLModel session (caller scope).
        provider: InsightProvider (từ factory theo settings).
        user_id: đã authenticate.
        request: body (range_preset, start/end, force).

    Returns:
        `GenerateResult` với snapshot, payload, range metadata.
    """
    preset_enum, current, previous = _resolve_ranges(
        request.range,
        request.start_date,
        request.end_date,
    )
    preset_str = preset_enum.value
    analytics = compute_summary(session, user_id, current, previous)

    summary = build_summary_input(
        session,
        user_id,
        preset_str,
        current,
        analytics,
    )
    fingerprint = summary.fingerprint()

    # Cache lookup (skip nếu force=True).
    if not request.force:
        cached = _find_cached_snapshot(session, user_id, fingerprint)
        if cached is not None:
            logger.info(
                "insights.cache_hit user_id=%s fingerprint=%s snapshot_id=%s",
                user_id,
                fingerprint[:12],
                cached.id,
            )
            return GenerateResult(
                snapshot=cached,
                payload=snapshot_to_payload(cached),
                range_=current,
                cached=True,
                fingerprint=fingerprint,
                status=cast(InsightStatus, cached.status),
                status_reason=cached.status_reason,
            )

    # Eligibility check.
    eligibility = check_eligibility(summary)
    if not eligibility.eligible:
        reason = eligibility.reason or "Không đủ điều kiện sinh insight."
        snapshot = _persist_snapshot(
            session,
            user_id=user_id,
            range_preset=preset_str,
            range_=current,
            provider_name=provider.name,
            fingerprint=fingerprint,
            payload=_empty_payload(),
            status="insufficient_data",
            status_reason=reason,
        )
        logger.info(
            "insights.insufficient_data user_id=%s reason_code=%s",
            user_id,
            eligibility.reason_code,
        )
        return GenerateResult(
            snapshot=snapshot,
            payload=_empty_payload(),
            range_=current,
            cached=False,
            fingerprint=fingerprint,
            status="insufficient_data",
            status_reason=reason,
        )

    # Call provider. Nếu lỗi → fallback snapshot.
    try:
        raw_payload = provider.generate(summary)
    except InsightProviderError as exc:
        logger.exception(
            "insights.provider_error user_id=%s provider=%s",
            user_id,
            provider.name,
        )
        snapshot = _persist_snapshot(
            session,
            user_id=user_id,
            range_preset=preset_str,
            range_=current,
            provider_name=provider.name,
            fingerprint=fingerprint,
            payload=_empty_payload(),
            status="failed",
            status_reason=str(exc)[:500],
        )
        return GenerateResult(
            snapshot=snapshot,
            payload=_empty_payload(),
            range_=current,
            cached=False,
            fingerprint=fingerprint,
            status="failed",
            status_reason=str(exc),
        )

    # Safety + grounding checks.
    report = run_safety_checks(raw_payload, summary)
    if report.violations:
        logger.warning(
            "insights.safety_violations user_id=%s count=%s kinds=%s",
            user_id,
            len(report.violations),
            sorted({v.kind for v in report.violations}),
        )

    snapshot = _persist_snapshot(
        session,
        user_id=user_id,
        range_preset=preset_str,
        range_=current,
        provider_name=provider.name,
        fingerprint=fingerprint,
        payload=report.filtered,
        status="ready",
        status_reason=None,
    )
    logger.info(
        "insights.generated user_id=%s provider=%s fingerprint=%s snapshot_id=%s "
        "insights=%s recommendations=%s alerts=%s",
        user_id,
        provider.name,
        fingerprint[:12],
        snapshot.id,
        len(report.filtered.insights),
        len(report.filtered.recommendations),
        len(report.filtered.alerts),
    )
    return GenerateResult(
        snapshot=snapshot,
        payload=report.filtered,
        range_=current,
        cached=False,
        fingerprint=fingerprint,
        status="ready",
        status_reason=None,
    )


def find_latest_snapshot(
    session: Session,
    user_id: int,
    range_preset: str,
) -> InsightSnapshot | None:
    """Lấy snapshot mới nhất của (user, preset). Dùng cho GET /insights/latest."""
    statement = (
        select(InsightSnapshot)
        .where(InsightSnapshot.user_id == user_id)
        .where(InsightSnapshot.range_preset == range_preset)
        .order_by(col(InsightSnapshot.created_at).desc())
        .limit(1)
    )
    return session.exec(statement).first()


def snapshot_generated_at(snapshot: InsightSnapshot) -> str:
    """ISO format UTC cho response. Tránh mismatch timezone giữa DB/UI."""
    ts = snapshot.created_at
    if ts.tzinfo is None:
        # SQLite lưu naive → assume UTC.
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC).isoformat()


# Re-export cho worker dùng.
__all__ = [
    "GenerateResult",
    "find_latest_snapshot",
    "generate_insight_for_user",
    "snapshot_generated_at",
    "snapshot_to_payload",
]
