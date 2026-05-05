"""Pydantic schemas cho AI insights (Phase 6).

Structure output:
- `insights[]`: quan sát trung tính (VD: "Chi tiêu ăn uống chiếm 40%").
- `recommendations[]`: đề xuất hành động (VD: "Giảm 10% chi Grab tháng sau").
- `alerts[]`: cảnh báo quan trọng (VD: "Budget ăn uống đã vượt 120%").

Field constraints giới hạn độ dài/số lượng để:
- LLM không ra câu quá dài (tránh spam UI).
- Parse output ổn định (payload JSON không quá lớn).
- Safety: limit số claim → kiểm tra grounding dễ hơn.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Hard caps: match MAX_* trong services.insights.safety.
MAX_TITLE_LEN = 120
MAX_BODY_LEN = 400
MAX_REASON_LEN = 200
MAX_INSIGHTS = 5
MAX_RECOMMENDATIONS = 5
MAX_ALERTS = 5


Severity = Literal["info", "warning", "critical"]
InsightStatus = Literal["ready", "insufficient_data", "failed"]


class InsightItem(BaseModel):
    """Quan sát trung tính về hành vi chi tiêu."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=MAX_TITLE_LEN)
    body: str = Field(min_length=1, max_length=MAX_BODY_LEN)
    # Tham chiếu category (nếu insight gắn với 1 category cụ thể).
    category_id: int | None = Field(default=None, ge=1)


class RecommendationItem(BaseModel):
    """Đề xuất hành động cụ thể, actionable."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=MAX_TITLE_LEN)
    body: str = Field(min_length=1, max_length=MAX_BODY_LEN)
    # Ước lượng tiết kiệm nếu làm theo (VND). None nếu không đo được.
    estimated_savings: str | None = Field(default=None, max_length=32)
    category_id: int | None = Field(default=None, ge=1)


class AlertItem(BaseModel):
    """Cảnh báo có độ ưu tiên (warning/critical). Luôn gắn severity."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=MAX_TITLE_LEN)
    body: str = Field(min_length=1, max_length=MAX_BODY_LEN)
    severity: Severity = "warning"
    category_id: int | None = Field(default=None, ge=1)


class InsightPayload(BaseModel):
    """Output chuẩn cho mọi provider (Mock/Ollama/Gemini). Provider phải
    trả đúng shape này — nếu LLM trả free-form text, provider adapter tự
    parse về đây (fail → raise InsightProviderError).
    """

    model_config = ConfigDict(extra="forbid")

    insights: list[InsightItem] = Field(default_factory=list, max_length=MAX_INSIGHTS)
    recommendations: list[RecommendationItem] = Field(
        default_factory=list,
        max_length=MAX_RECOMMENDATIONS,
    )
    alerts: list[AlertItem] = Field(default_factory=list, max_length=MAX_ALERTS)


# --- API response shapes ---


class InsightRangeInfo(BaseModel):
    preset: str
    start: date
    end: date


class InsightResponse(BaseModel):
    """Response cho POST /insights/generate và GET /insights/latest.

    Khi `status != "ready"`, `payload` vẫn có 3 arrays nhưng thường rỗng;
    UI dựa `status` + `status_reason` hiển thị fallback thay vì cards.
    """

    model_config = ConfigDict(extra="forbid")

    id: int | None = None  # None khi chỉ là fallback in-memory, chưa lưu DB.
    range: InsightRangeInfo
    status: InsightStatus
    status_reason: str | None = None
    provider: str
    fingerprint: str
    payload: InsightPayload
    generated_at: str  # ISO datetime (UTC).
    # True nếu response là cache hit — UI có thể hiển thị badge "đã cache".
    cached: bool = False


class GenerateInsightRequest(BaseModel):
    """Body cho POST /insights/generate (optional — mặc định dùng query)."""

    model_config = ConfigDict(extra="forbid")

    range: str = Field(default="30d", min_length=2, max_length=20)
    start_date: date | None = None
    end_date: date | None = None
    # Force regenerate bỏ qua cache (ví dụ user click "Refresh").
    force: bool = False


__all__ = [
    "AlertItem",
    "GenerateInsightRequest",
    "InsightItem",
    "InsightPayload",
    "InsightRangeInfo",
    "InsightResponse",
    "InsightStatus",
    "RecommendationItem",
    "Severity",
    "MAX_ALERTS",
    "MAX_BODY_LEN",
    "MAX_INSIGHTS",
    "MAX_RECOMMENDATIONS",
    "MAX_TITLE_LEN",
]
