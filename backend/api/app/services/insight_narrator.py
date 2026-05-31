"""LLM narration cho insight (B2).

Giữ số liệu deterministic làm nguồn sự thật. LLM CHỈ viết lại câu chữ
(`title`/`summary`) cho tự nhiên, KHÔNG được sinh số mới.

Nguyên tắc:
- Fail-soft: lỗi mạng/timeout/parse/cấu hình → trả None, caller giữ text gốc.
- Chống bịa số: prompt yêu cầu LLM chỉ diễn đạt lại từ evidence cho sẵn,
  không thêm/bớt con số. Nếu output rỗng hoặc bất thường → bỏ.
- Quyền riêng tư: caller chịu trách nhiệm chỉ gọi khi user bật
  `allow_ai_data_processing`.
- Đồng bộ: httpx sync, timeout ngắn (insight feed không nên chờ lâu).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("api.insight_narrator")

NARRATE_TIMEOUT_SECONDS = 12.0
MAX_TITLE_LEN = 120
MAX_SUMMARY_LEN = 400


@dataclass(frozen=True, slots=True)
class NarratedText:
    title: str
    summary: str


def _build_prompt(
    *,
    insight_type: str,
    base_title: str,
    base_summary: str,
    evidence: list[dict[str, Any]],
) -> str:
    evidence_json = json.dumps(evidence, ensure_ascii=False)
    return (
        "Bạn là trợ lý tài chính cá nhân nói tiếng Việt. Viết lại tiêu đề và "
        "mô tả cho một insight chi tiêu sao cho tự nhiên, ngắn gọn, thân thiện.\n\n"
        "QUY TẮC BẮT BUỘC:\n"
        "- CHỈ diễn đạt lại dựa trên dữ liệu cho sẵn. TUYỆT ĐỐI không bịa thêm "
        "con số, ngày tháng, danh mục hay cửa hàng mới.\n"
        "- Giữ nguyên mọi con số (số tiền, phần trăm) đúng như dữ liệu gốc.\n"
        "- Tiêu đề ngắn (tối đa ~12 từ). Mô tả 1-2 câu.\n"
        "- Không markdown, không emoji.\n\n"
        f"Loại insight: {insight_type}\n"
        f"Tiêu đề gốc: {base_title}\n"
        f"Mô tả gốc: {base_summary}\n"
        f"Dữ liệu (evidence): {evidence_json}\n\n"
        'Trả về DUY NHẤT JSON: {"title": "...", "summary": "..."}. '
        "Không thêm giải thích."
    )


def _parse_response(content: str) -> NarratedText | None:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    title = str(data.get("title") or "").strip()
    summary = str(data.get("summary") or "").strip()
    if not title or not summary:
        return None
    return NarratedText(title=title[:MAX_TITLE_LEN], summary=summary[:MAX_SUMMARY_LEN])


def narrate_insight(
    *,
    insight_type: str,
    base_title: str,
    base_summary: str,
    evidence: list[dict[str, Any]],
) -> NarratedText | None:
    """Diễn giải lại insight bằng LLM. Trả None nếu không khả dụng (fail-soft)."""
    settings = get_settings()
    base_url = (settings.chat_llm_base_url or "").strip()
    api_key = (settings.chat_llm_api_key or "").strip()
    model = (settings.chat_llm_model or "").strip()
    if not (base_url and api_key and model):
        return None

    prompt = _build_prompt(
        insight_type=insight_type,
        base_title=base_title,
        base_summary=base_summary,
        evidence=evidence,
    )
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
            },
            timeout=NARRATE_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            logger.warning(
                "insight_narrator.http_error status=%d body=%s",
                response.status_code,
                response.text[:200],
            )
            return None
        data = response.json()
        content = data["choices"][0]["message"].get("content", "") or ""
    except Exception as exc:  # noqa: BLE001 - fail-soft, không chặn feed
        logger.warning("insight_narrator.failed error=%s", str(exc)[:200])
        return None

    return _parse_response(content)


__all__ = ["NarratedText", "narrate_insight"]
