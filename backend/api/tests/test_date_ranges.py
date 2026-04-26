"""Unit tests cho `app.services.date_ranges` (Phase 4.1).

Test deterministic bằng cách inject `today` parameter — không phụ thuộc
real wall-clock.
"""
from __future__ import annotations

from datetime import date

import pytest
from app.services.date_ranges import (
    DateRange,
    InvalidDateRangeError,
    RangePreset,
    previous_period,
    resolve_range,
)


class TestResolveRange:
    def test_last_7_days_inclusive(self) -> None:
        # today = 2026-04-15 → range = 2026-04-09 ~ 2026-04-15 (7 days inclusive).
        today = date(2026, 4, 15)
        result = resolve_range(RangePreset.LAST_7_DAYS, today=today)
        assert result == DateRange(start=date(2026, 4, 9), end=date(2026, 4, 15))
        assert result.days == 7

    def test_last_30_days_inclusive(self) -> None:
        today = date(2026, 4, 15)
        result = resolve_range(RangePreset.LAST_30_DAYS, today=today)
        assert result.start == date(2026, 3, 17)
        assert result.end == today
        assert result.days == 30

    def test_this_month_from_first_to_today(self) -> None:
        today = date(2026, 4, 15)
        result = resolve_range(RangePreset.THIS_MONTH, today=today)
        assert result.start == date(2026, 4, 1)
        assert result.end == date(2026, 4, 15)

    def test_this_month_on_first_of_month(self) -> None:
        # Edge: hôm nay là ngày 1 → range chỉ có 1 ngày.
        today = date(2026, 4, 1)
        result = resolve_range(RangePreset.THIS_MONTH, today=today)
        assert result.start == today
        assert result.end == today
        assert result.days == 1

    def test_last_month_full_range(self) -> None:
        today = date(2026, 4, 15)
        result = resolve_range(RangePreset.LAST_MONTH, today=today)
        # Tháng 3 có 31 ngày.
        assert result.start == date(2026, 3, 1)
        assert result.end == date(2026, 3, 31)
        assert result.days == 31

    def test_last_month_february_leap_year(self) -> None:
        # 2024 là năm nhuận → February có 29 ngày.
        today = date(2024, 3, 5)
        result = resolve_range(RangePreset.LAST_MONTH, today=today)
        assert result.start == date(2024, 2, 1)
        assert result.end == date(2024, 2, 29)

    def test_last_month_february_non_leap(self) -> None:
        today = date(2026, 3, 5)
        result = resolve_range(RangePreset.LAST_MONTH, today=today)
        assert result.start == date(2026, 2, 1)
        assert result.end == date(2026, 2, 28)

    def test_last_month_january_crosses_year(self) -> None:
        today = date(2026, 1, 5)
        result = resolve_range(RangePreset.LAST_MONTH, today=today)
        assert result.start == date(2025, 12, 1)
        assert result.end == date(2025, 12, 31)

    def test_custom_range_happy_path(self) -> None:
        result = resolve_range(
            RangePreset.CUSTOM,
            custom_start=date(2026, 4, 1),
            custom_end=date(2026, 4, 10),
        )
        assert result.start == date(2026, 4, 1)
        assert result.end == date(2026, 4, 10)
        assert result.days == 10

    def test_custom_range_missing_start_raises(self) -> None:
        with pytest.raises(InvalidDateRangeError, match="Custom preset requires"):
            resolve_range(
                RangePreset.CUSTOM,
                custom_start=None,
                custom_end=date(2026, 4, 10),
            )

    def test_custom_range_start_after_end_raises(self) -> None:
        with pytest.raises(InvalidDateRangeError, match="must be <="):
            resolve_range(
                RangePreset.CUSTOM,
                custom_start=date(2026, 4, 10),
                custom_end=date(2026, 4, 1),
            )

    def test_custom_range_too_long_raises(self) -> None:
        with pytest.raises(InvalidDateRangeError, match="cannot exceed"):
            resolve_range(
                RangePreset.CUSTOM,
                custom_start=date(2024, 1, 1),
                custom_end=date(2026, 1, 1),  # ~ 2 years.
            )


class TestPreviousPeriod:
    def test_previous_for_7d_is_prior_7_days(self) -> None:
        current = DateRange(start=date(2026, 4, 9), end=date(2026, 4, 15))
        result = previous_period(current, RangePreset.LAST_7_DAYS)
        # 7 ngày kết thúc ngay trước 2026-04-09 → 2026-04-02 ~ 2026-04-08.
        assert result.start == date(2026, 4, 2)
        assert result.end == date(2026, 4, 8)
        assert result.days == 7

    def test_previous_for_30d_is_prior_30_days(self) -> None:
        current = DateRange(start=date(2026, 3, 17), end=date(2026, 4, 15))
        result = previous_period(current, RangePreset.LAST_30_DAYS)
        assert result.end == date(2026, 3, 16)
        assert result.days == 30

    def test_previous_for_this_month_is_full_last_month(self) -> None:
        # this_month tháng 4 (1->15) → previous = full tháng 3.
        current = DateRange(start=date(2026, 4, 1), end=date(2026, 4, 15))
        result = previous_period(current, RangePreset.THIS_MONTH)
        assert result.start == date(2026, 3, 1)
        assert result.end == date(2026, 3, 31)

    def test_previous_for_last_month_is_full_month_before(self) -> None:
        # current là full tháng 3 → previous = full tháng 2.
        current = DateRange(start=date(2026, 3, 1), end=date(2026, 3, 31))
        result = previous_period(current, RangePreset.LAST_MONTH)
        assert result.start == date(2026, 2, 1)
        assert result.end == date(2026, 2, 28)

    def test_previous_for_custom_keeps_same_length(self) -> None:
        current = DateRange(start=date(2026, 4, 1), end=date(2026, 4, 10))
        result = previous_period(current, RangePreset.CUSTOM)
        # 10 days ending 2026-03-31 → 2026-03-22 ~ 2026-03-31.
        assert result.start == date(2026, 3, 22)
        assert result.end == date(2026, 3, 31)
        assert result.days == 10

    def test_previous_crosses_year_boundary(self) -> None:
        current = DateRange(start=date(2026, 1, 1), end=date(2026, 1, 7))
        result = previous_period(current, RangePreset.LAST_7_DAYS)
        assert result.start == date(2025, 12, 25)
        assert result.end == date(2025, 12, 31)
