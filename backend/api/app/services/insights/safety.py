"""Safety + grounding checks cho insight output (Phase 6.8).

Mục tiêu:
1. Detect banned phrases (investment, crypto advice, ...) để filter.
2. Verify `category_id` được reference trong output phải tồn tại trong
   SummaryInput (không phải LLM hallucinate).
3. Flag items vi phạm → caller quyết định drop hay fallback.

Trả về `SafetyReport` với danh sách vi phạm + output đã filtered (giữ
items hợp lệ). Không mutate input, trả copy mới.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.insights import (
    AlertItem,
    InsightItem,
    InsightPayload,
    RecommendationItem,
)
from app.services.insights.summary import SummaryInput

# Danh sách cụm từ bị cấm (case-insensitive substring match). Giữ tối
# thiểu để tránh false-positive; mở rộng khi cần.
BANNED_PHRASES: tuple[str, ...] = (
    "đầu tư chứng khoán",
    "cổ phiếu",
    "bitcoin",
    "crypto",
    "forex",
    "vay tiền nhanh",
    "lãi suất",
    "bảo hiểm nhân thọ",
    "tư vấn pháp lý",
    "tư vấn y tế",
)


@dataclass(frozen=True, slots=True)
class Violation:
    """1 vi phạm. `kind` machine-readable; `detail` người đọc."""

    kind: str  # "banned_phrase" | "unknown_category" | "empty_text"
    section: str  # "insights" | "recommendations" | "alerts"
    index: int
    detail: str


@dataclass(frozen=True, slots=True)
class SafetyReport:
    """Kết quả chạy safety checks."""

    violations: list[Violation] = field(default_factory=list)
    # Output đã filter bỏ items vi phạm. Giữ các items OK theo thứ tự gốc.
    filtered: InsightPayload = field(default_factory=InsightPayload)

    @property
    def ok(self) -> bool:
        return not self.violations


def _contains_banned(text: str) -> str | None:
    """Return banned phrase nếu text chứa nó, else None."""
    lower = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower:
            return phrase
    return None


def _check_item_text(
    section: str,
    index: int,
    title: str,
    body: str,
) -> list[Violation]:
    """Kiểm tra title + body có banned phrase hoặc empty không."""
    violations: list[Violation] = []
    for field_name, text in (("title", title), ("body", body)):
        stripped = text.strip()
        if not stripped:
            violations.append(
                Violation(
                    kind="empty_text",
                    section=section,
                    index=index,
                    detail=f"{field_name} rỗng sau khi trim",
                ),
            )
            continue
        banned = _contains_banned(stripped)
        if banned is not None:
            violations.append(
                Violation(
                    kind="banned_phrase",
                    section=section,
                    index=index,
                    detail=f"{field_name} chứa cụm bị cấm: '{banned}'",
                ),
            )
    return violations


def run_safety_checks(
    payload: InsightPayload,
    summary: SummaryInput,
) -> SafetyReport:
    """Chạy toàn bộ safety + grounding checks.

    Rule grounding:
    - `category_id` phải nằm trong set `{c.category_id for c in top_categories}`
      ∪ `{b.category_id for b in budgets}` ∪ `{a.category_id for a in anomalies}`.
      Nếu LLM reference category không có trong summary → drop.
    - Text không được chứa banned phrases.
    - Text không được rỗng (Pydantic đã check min_length=1 nhưng phòng
      LLM gửi whitespace-only).

    Items vi phạm bị loại khỏi `filtered`. Report trả toàn bộ violations
    để logger audit + UI hint nếu cần.
    """
    known_category_ids: set[int] = set()
    for c in summary.analytics.top_categories:
        if c.category_id is not None:
            known_category_ids.add(c.category_id)
    for b in summary.budgets:
        known_category_ids.add(b.category_id)
    for a in summary.anomalies:
        if a.category_id is not None:
            known_category_ids.add(a.category_id)

    violations: list[Violation] = []

    kept_insights: list[InsightItem] = []
    for i, item in enumerate(payload.insights):
        item_violations = _check_item_text("insights", i, item.title, item.body)
        if item.category_id is not None and item.category_id not in known_category_ids:
            item_violations.append(
                Violation(
                    kind="unknown_category",
                    section="insights",
                    index=i,
                    detail=f"category_id={item.category_id} không có trong summary",
                ),
            )
        if item_violations:
            violations.extend(item_violations)
        else:
            kept_insights.append(item)

    kept_recs: list[RecommendationItem] = []
    for i, rec in enumerate(payload.recommendations):
        item_violations = _check_item_text(
            "recommendations",
            i,
            rec.title,
            rec.body,
        )
        if rec.category_id is not None and rec.category_id not in known_category_ids:
            item_violations.append(
                Violation(
                    kind="unknown_category",
                    section="recommendations",
                    index=i,
                    detail=f"category_id={rec.category_id} không có trong summary",
                ),
            )
        if item_violations:
            violations.extend(item_violations)
        else:
            kept_recs.append(rec)

    kept_alerts: list[AlertItem] = []
    for i, alert in enumerate(payload.alerts):
        item_violations = _check_item_text(
            "alerts",
            i,
            alert.title,
            alert.body,
        )
        if alert.category_id is not None and alert.category_id not in known_category_ids:
            item_violations.append(
                Violation(
                    kind="unknown_category",
                    section="alerts",
                    index=i,
                    detail=f"category_id={alert.category_id} không có trong summary",
                ),
            )
        if item_violations:
            violations.extend(item_violations)
        else:
            kept_alerts.append(alert)

    filtered = InsightPayload(
        insights=kept_insights,
        recommendations=kept_recs,
        alerts=kept_alerts,
    )
    return SafetyReport(violations=violations, filtered=filtered)


__all__ = [
    "BANNED_PHRASES",
    "SafetyReport",
    "Violation",
    "run_safety_checks",
]
