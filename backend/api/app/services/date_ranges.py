"""Date range helpers cho dashboard analytics (Phase 4.1).

Cung cấp:
- `RangePreset` enum: "7d" | "30d" | "this_month" | "last_month" | "custom".
- `resolve_range(preset, custom_start, custom_end, today)` → `(start, end)` tuple
  với `start` và `end` đều inclusive (date object, không có time).
- `previous_period(start, end, preset)` → range tương đương trước đó để so sánh.

Quy ước:
- Tất cả range là inclusive cả 2 đầu (start <= d <= end). SQL dùng `BETWEEN`
  hoặc `>=` + `<=` để match.
- "this_month" = từ ngày 1 → ngày hôm nay (không phải tới cuối tháng).
- "last_month" = full tháng trước (ngày 1 → ngày cuối tháng đó).
- "7d" / "30d" = N ngày gần nhất tính cả hôm nay (vd 7d = today - 6 → today).

Previous period:
- 7d / 30d / custom: cùng độ dài N ngày, kết thúc ngay trước `start`.
- this_month: full tháng trước (giống last_month).
- last_month: tháng trước nữa.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class RangePreset(StrEnum):
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date
    end: date

    @property
    def days(self) -> int:
        """Số ngày trong range (inclusive cả 2 đầu)."""
        return (self.end - self.start).days + 1


class InvalidDateRangeError(ValueError):
    """Raise khi custom range không hợp lệ (start > end, vượt quá max days,...)."""


# Giới hạn custom range để tránh query quá nặng (1 năm là đủ rộng cho
# dashboard cá nhân; nếu cần xa hơn người dùng nên export CSV).
MAX_CUSTOM_RANGE_DAYS = 366


def _last_day_of_month(year: int, month: int) -> int:
    """Trả về số ngày trong tháng (year, month). Tránh phụ thuộc calendar lib."""
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    last_day = next_month_first - timedelta(days=1)
    return last_day.day


def _previous_month(year: int, month: int) -> tuple[int, int]:
    """Trả `(year, month)` của tháng trước."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


def resolve_range(
    preset: RangePreset,
    custom_start: date | None = None,
    custom_end: date | None = None,
    today: date | None = None,
) -> DateRange:
    """Trả `DateRange(start, end)` cho preset đã chọn.

    `today` mặc định là `date.today()`; nhận parameter để test deterministic.
    Custom preset yêu cầu cả `custom_start` và `custom_end`.
    """
    today = today or date.today()

    if preset is RangePreset.LAST_7_DAYS:
        return DateRange(start=today - timedelta(days=6), end=today)

    if preset is RangePreset.LAST_30_DAYS:
        return DateRange(start=today - timedelta(days=29), end=today)

    if preset is RangePreset.THIS_MONTH:
        first_of_month = today.replace(day=1)
        return DateRange(start=first_of_month, end=today)

    if preset is RangePreset.LAST_MONTH:
        prev_year, prev_month = _previous_month(today.year, today.month)
        last_day = _last_day_of_month(prev_year, prev_month)
        return DateRange(
            start=date(prev_year, prev_month, 1),
            end=date(prev_year, prev_month, last_day),
        )

    # CUSTOM
    if custom_start is None or custom_end is None:
        raise InvalidDateRangeError(
            "Custom preset requires both custom_start and custom_end",
        )
    if custom_start > custom_end:
        raise InvalidDateRangeError(
            f"custom_start ({custom_start}) must be <= custom_end ({custom_end})",
        )
    days = (custom_end - custom_start).days + 1
    if days > MAX_CUSTOM_RANGE_DAYS:
        raise InvalidDateRangeError(
            f"Custom range cannot exceed {MAX_CUSTOM_RANGE_DAYS} days "
            f"(got {days} days)",
        )
    return DateRange(start=custom_start, end=custom_end)


def previous_period(current: DateRange, preset: RangePreset) -> DateRange:
    """Trả range trước đó để so sánh delta.

    - 7d / 30d / custom: cùng độ dài N ngày, kết thúc ngay trước `current.start`.
    - this_month / last_month: tháng trước (full).
    """
    if preset is RangePreset.THIS_MONTH:
        prev_year, prev_month = _previous_month(current.start.year, current.start.month)
        last_day = _last_day_of_month(prev_year, prev_month)
        return DateRange(
            start=date(prev_year, prev_month, 1),
            end=date(prev_year, prev_month, last_day),
        )

    if preset is RangePreset.LAST_MONTH:
        # current đang là last month → previous = tháng trước nữa.
        prev_year, prev_month = _previous_month(current.start.year, current.start.month)
        last_day = _last_day_of_month(prev_year, prev_month)
        return DateRange(
            start=date(prev_year, prev_month, 1),
            end=date(prev_year, prev_month, last_day),
        )

    # 7d / 30d / custom: rolling window cùng kích thước.
    days = current.days
    end = current.start - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return DateRange(start=start, end=end)


__all__ = [
    "MAX_CUSTOM_RANGE_DAYS",
    "DateRange",
    "InvalidDateRangeError",
    "RangePreset",
    "previous_period",
    "resolve_range",
]
