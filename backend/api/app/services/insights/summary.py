"""Summary input builder (Phase 6.1).

Chuyển dữ liệu cấu trúc (analytics + budgets) thành 1 dict deterministic
để truyền cho LLM provider. Output được SHA256 hash → fingerprint dùng
cho caching.

Rules:
- Chỉ dùng giá trị đã được compute từ DB (không tự tạo giá trị giả).
- Decimal → string với precision cố định → hash stable giữa các runs.
- Keys sort theo alphabetical → JSON canonical form.
- Không include timestamp/id tự sinh → 2 lần build cùng DB state ra cùng
  fingerprint (điều kiện cho cache hit).

Schema của summary dict (`SummaryInput.to_dict()`):
```
{
  "range": {"preset": "30d", "start": "2026-04-05", "end": "2026-05-05", "days": 31},
  "current": {"total_spend": "1500000.00", "transaction_count": 42},
  "previous": {"total_spend": "1200000.00", "transaction_count": 38},
  "delta": {"amount": "300000.00", "percent": 25.0},
  "top_categories": [
    {"category_id": 1, "name": "Ăn uống", "total": "800000.00", "count": 20, "percentage": 53.33},
    ...
  ],
  "budgets": [
    {"category_id": 1, "name": "Ăn uống", "budget": "1000000.00", "spent": "800000.00",
     "percent_used": 80.0, "status": "warning"},
    ...
  ],
  "anomalies": [
    {"kind": "large_transaction", "amount": "500000.00", "date": "2026-04-30",
     "merchant_name": "ABC", "category_id": 3},
    ...
  ]
}
```
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlmodel import Session, col, select

from app.models.entities import Transaction
from app.services.analytics import DashboardSummary
from app.services.budgets import BudgetUsage, compute_budget_usage
from app.services.date_ranges import DateRange

# Threshold: giao dịch lớn hơn `ANOMALY_MULTIPLIER × median` được gắn cờ.
# Dùng median (robust với outlier) thay vì mean → ít false-positive hơn.
ANOMALY_MULTIPLIER = Decimal("3.0")
# Ngưỡng tối thiểu amount để xét anomaly (tránh báo động với micro-spend).
ANOMALY_MIN_ABSOLUTE = Decimal("100000")  # 100k VND.
# Giới hạn số anomaly đưa vào prompt — LLM không cần list quá dài.
ANOMALY_MAX_ITEMS = 5


@dataclass(frozen=True, slots=True)
class AnomalyCandidate:
    """Giao dịch lớn bất thường so với thói quen chi tiêu trong range."""

    kind: str  # "large_transaction" hiện tại; mở rộng sau: "unusual_merchant", ...
    transaction_id: int
    amount: Decimal
    transaction_date: date
    merchant_name: str | None
    category_id: int | None


@dataclass(frozen=True, slots=True)
class SummaryInput:
    """Input deterministic cho LLM. Dùng `to_dict()` để serialize + hash."""

    range_preset: str
    range_start: date
    range_end: date
    analytics: DashboardSummary
    budgets: list[BudgetUsage] = field(default_factory=list)
    anomalies: list[AnomalyCandidate] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize về primitive types JSON-safe. Decimal → string,
        date → ISO, float → float. Các list đã được sort ở builder.
        """
        days = (self.range_end - self.range_start).days + 1
        return {
            "range": {
                "preset": self.range_preset,
                "start": self.range_start.isoformat(),
                "end": self.range_end.isoformat(),
                "days": days,
            },
            "current": {
                "total_spend": _decimal_str(self.analytics.current.total_spend),
                "transaction_count": self.analytics.current.transaction_count,
            },
            "previous": {
                "total_spend": _decimal_str(self.analytics.previous.total_spend),
                "transaction_count": self.analytics.previous.transaction_count,
            },
            "delta": {
                "amount": _decimal_str(self.analytics.delta_amount),
                "percent": self.analytics.delta_percent,
            },
            "top_categories": [
                {
                    "category_id": c.category_id,
                    "name": c.name,
                    "total": _decimal_str(c.total_amount),
                    "count": c.transaction_count,
                    "percentage": c.percentage,
                }
                for c in self.analytics.top_categories
            ],
            "budgets": [
                {
                    "budget_id": b.budget_id,
                    "category_id": b.category_id,
                    "name": b.category_name,
                    "budget": _decimal_str(b.budget_amount),
                    "spent": _decimal_str(b.spent_amount),
                    "percent_used": b.percent_used,
                    "status": b.status,
                }
                for b in self.budgets
            ],
            "anomalies": [
                {
                    "kind": a.kind,
                    "transaction_id": a.transaction_id,
                    "amount": _decimal_str(a.amount),
                    "date": a.transaction_date.isoformat(),
                    "merchant_name": a.merchant_name,
                    "category_id": a.category_id,
                }
                for a in self.anomalies
            ],
        }

    def fingerprint(self) -> str:
        """SHA256 hex của JSON canonical form. Stable giữa các runs với
        cùng DB state → dùng cho cache key `(user_id, fingerprint)`.

        `sort_keys=True` + `separators=(",",":")` để output 1 hash duy nhất
        cho cùng dict, không phụ thuộc thứ tự insert.
        """
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decimal_str(value: Decimal) -> str:
    """Format Decimal với 2 chữ số thập phân. Stable với cả currency
    fractional (USD 10.50) và VND (1500000.00).

    Quan trọng: Decimal("1500000") và Decimal("1500000.00") serialize
    khác nhau → chuẩn hóa sang 2 chữ số để fingerprint không đổi khi DB
    trả format khác.
    """
    return f"{value:.2f}"


def _collect_anomalies(
    session: Session,
    user_id: int,
    range_: DateRange,
) -> list[AnomalyCandidate]:
    """Tìm các transaction có amount >> median × ANOMALY_MULTIPLIER.

    Dùng median thay vì mean để robust với skewed distribution (1 giao
    dịch rất lớn không làm lệch ngưỡng).

    Returns top N (=ANOMALY_MAX_ITEMS) theo amount DESC.
    """
    statement = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .order_by(col(Transaction.amount).desc())
    )
    rows = list(session.exec(statement).all())
    if len(rows) < 3:
        # Không đủ data để tính median đáng tin — bỏ qua.
        return []

    amounts = sorted(t.amount for t in rows)
    n = len(amounts)
    if n % 2 == 1:
        median = amounts[n // 2]
    else:
        median = (amounts[n // 2 - 1] + amounts[n // 2]) / Decimal(2)

    threshold = max(median * ANOMALY_MULTIPLIER, ANOMALY_MIN_ABSOLUTE)

    candidates: list[AnomalyCandidate] = []
    for t in rows:
        if t.amount < threshold:
            # Rows đã sort DESC → dừng sớm khi gặp value nhỏ hơn threshold.
            break
        if t.id is None:
            continue
        candidates.append(
            AnomalyCandidate(
                kind="large_transaction",
                transaction_id=t.id,
                amount=t.amount,
                transaction_date=t.transaction_date,
                merchant_name=t.merchant_name,
                category_id=t.category_id,
            ),
        )
        if len(candidates) >= ANOMALY_MAX_ITEMS:
            break
    return candidates


def build_summary_input(
    session: Session,
    user_id: int,
    range_preset: str,
    current: DateRange,
    analytics: DashboardSummary,
) -> SummaryInput:
    """Gộp analytics + budgets + anomalies thành `SummaryInput`.

    Budgets: lấy từ tháng của `current.end` (dashboard đã dùng logic này),
    để insight nói về budget đang active nhất trong range.

    Anomalies: scan toàn bộ range (không cần chia theo month).
    """
    budget_period = f"{current.end.year:04d}-{current.end.month:02d}"
    budgets = compute_budget_usage(session, user_id, budget_period)
    anomalies = _collect_anomalies(session, user_id, current)
    return SummaryInput(
        range_preset=range_preset,
        range_start=current.start,
        range_end=current.end,
        analytics=analytics,
        budgets=list(budgets),
        anomalies=anomalies,
    )


def safe_delta_percent(current: Decimal, previous: Decimal) -> float | None:
    """Helper — trả None nếu previous=0 (tránh ZeroDivisionError).
    Dùng ở builder + safety check khi cần verify tính toán của LLM.
    """
    if previous == Decimal("0"):
        return None
    delta = ((current - previous) / previous) * Decimal("100")
    return float(round(delta, 2))


# Helper để test: build minimal range mới từ preset + end date.
def _preset_days(preset: str) -> int | None:
    """Map preset → số ngày (None = dynamic như this_month)."""
    mapping = {"7d": 7, "30d": 30}
    return mapping.get(preset)


def range_end_to_start(preset: str, end: date) -> date:
    """Given preset + end → compute start. Dùng cho eligibility/tests."""
    days = _preset_days(preset)
    if days is not None:
        return end - timedelta(days=days - 1)
    # "this_month"/"last_month"/"custom" — caller phải tự xác định.
    return end


__all__ = [
    "ANOMALY_MAX_ITEMS",
    "ANOMALY_MIN_ABSOLUTE",
    "ANOMALY_MULTIPLIER",
    "AnomalyCandidate",
    "SummaryInput",
    "build_summary_input",
    "range_end_to_start",
    "safe_delta_percent",
]
