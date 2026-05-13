"""Safety layer cho chatbot (Phase 6.6).

- Banned phrases filter (tái sử dụng từ insight cũ).
- Rate limit in-memory per user.
"""
from __future__ import annotations

from collections import defaultdict
from time import monotonic

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

FALLBACK_MESSAGE = "Xin lỗi, mình chỉ hỗ trợ câu hỏi về chi tiêu cá nhân."


class RateLimitExceeded(Exception):
    """User vượt quá rate limit."""


# In-memory rate limit buckets: user_id → list of timestamps
_BUCKETS: dict[int, list[float]] = defaultdict(list)


def check_rate_limit(user_id: int, max_per_minute: int = 10) -> None:
    """Check rate limit. Raise RateLimitExceeded nếu vượt.

    Simple token bucket: giữ timestamps trong 60s gần nhất.
    """
    now = monotonic()
    bucket = _BUCKETS[user_id]
    # Remove timestamps older than 60s
    bucket[:] = [t for t in bucket if now - t < 60]
    if len(bucket) >= max_per_minute:
        raise RateLimitExceeded(
            f"Rate limit exceeded: {max_per_minute} requests/minute",
        )
    bucket.append(now)


def apply_safety_filter(content: str) -> str:
    """Filter banned phrases trong assistant response.

    Nếu content chứa banned phrase → return fallback message.
    """
    lower = content.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower:
            return FALLBACK_MESSAGE
    return content


def reset_rate_limits() -> None:
    """Reset tất cả buckets (dùng cho testing)."""
    _BUCKETS.clear()


__all__ = [
    "BANNED_PHRASES",
    "FALLBACK_MESSAGE",
    "RateLimitExceeded",
    "apply_safety_filter",
    "check_rate_limit",
    "reset_rate_limits",
]
