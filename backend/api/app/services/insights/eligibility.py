"""Eligibility rules (Phase 6.2).

Kiểm tra SummaryInput có đủ "meat" để sinh insight hay không. Nếu không,
trả về fallback response với `status=insufficient_data` + `reason`. Tránh
gọi LLM để ra những câu chung chung vô nghĩa.

Rules MVP:
- `MIN_TRANSACTIONS`: cần ít nhất N giao dịch trong range current.
- `MIN_DISTINCT_DAYS`: ít nhất K ngày riêng biệt có giao dịch (để tránh
  burst 1 ngày rồi dead silence).
- `MIN_TOTAL_SPEND`: total spend tối thiểu để insight có ý nghĩa.

Nới/thắt các con số trong `EligibilityRules` khi có feedback UAT thực tế.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.services.insights.summary import SummaryInput

MIN_TRANSACTIONS = 3
MIN_DISTINCT_DAYS = 2
MIN_TOTAL_SPEND = Decimal("50000")  # 50k VND.


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    """Output của check. `eligible=True` → đủ điều kiện gọi LLM."""

    eligible: bool
    reason: str | None = None
    # Key machine-readable để UI mapping sang thông điệp vi_VN.
    reason_code: str | None = None


def check_eligibility(
    summary: SummaryInput,
    *,
    min_transactions: int = MIN_TRANSACTIONS,
    min_distinct_days: int = MIN_DISTINCT_DAYS,
    min_total_spend: Decimal = MIN_TOTAL_SPEND,
) -> EligibilityResult:
    """Xét SummaryInput có đủ meaningful data không.

    Return `EligibilityResult(eligible=False, reason_code="...")` nếu fail
    bất kỳ rule nào. Caller dùng `reason_code` để render i18n message.
    """
    txn_count = summary.analytics.current.transaction_count
    if txn_count < min_transactions:
        return EligibilityResult(
            eligible=False,
            reason_code="too_few_transactions",
            reason=(
                f"Cần ít nhất {min_transactions} giao dịch trong kỳ để sinh insight"
                f" (hiện có {txn_count})."
            ),
        )

    total_spend = summary.analytics.current.total_spend
    if total_spend < min_total_spend:
        return EligibilityResult(
            eligible=False,
            reason_code="too_low_spend",
            reason=(
                f"Tổng chi tiêu trong kỳ ({total_spend}) chưa đủ ngưỡng tối thiểu"
                f" ({min_total_spend}) để sinh insight."
            ),
        )

    # Distinct days: đếm số ngày có transaction. Dùng recent_transactions
    # (đã load từ analytics) để tránh thêm 1 query — nếu recent < count
    # vì limit, ta vẫn OK vì đây là lower bound, sẽ conservative hơn.
    distinct_dates = {
        item.transaction_date for item in summary.analytics.recent_transactions
    }
    # Nếu transaction count lớn hơn recent limit mà tất cả cùng 1 ngày
    # thì recent list có thể chỉ show 1 date. Trong trường hợp này ta
    # không chắc 100% nhưng với MVP chấp nhận false-positive eligible.
    if txn_count <= len(summary.analytics.recent_transactions):
        # Chỉ apply rule khi recent list đã cover hết transactions.
        if len(distinct_dates) < min_distinct_days:
            return EligibilityResult(
                eligible=False,
                reason_code="too_concentrated",
                reason=(
                    f"Giao dịch tập trung vào {len(distinct_dates)} ngày — cần ít"
                    f" nhất {min_distinct_days} ngày khác nhau để sinh insight."
                ),
            )

    return EligibilityResult(eligible=True)


__all__ = [
    "MIN_DISTINCT_DAYS",
    "MIN_TOTAL_SPEND",
    "MIN_TRANSACTIONS",
    "EligibilityResult",
    "check_eligibility",
]
