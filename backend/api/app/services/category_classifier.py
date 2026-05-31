"""LLM-based category classifier (G1).

Phân loại merchant vào ĐÚNG MỘT category có sẵn của user bằng LLM (đồng bộ).

Nguyên tắc:
- Chống bịa: LLM phải chọn `id` nằm trong danh sách category truyền vào. Nếu trả
  id không hợp lệ / không chắc → coi như không phân loại (None).
- Fail-soft: lỗi mạng/timeout/parse → trả None, KHÔNG raise (không chặn luồng
  tạo transaction hay dựng draft).
- Đồng bộ: dùng httpx sync (giống `worker/ocr_provider.py`) vì caller
  (`category_suggestion`) là code sync trong request handler.
- Quyền riêng tư: caller chịu trách nhiệm chỉ gọi khi user bật
  `allow_ai_data_processing`.
"""
from __future__ import annotations

import json
import re

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("api.category_classifier")

# Timeout ngắn: phân loại chạy đồng bộ trong request nên không để chờ lâu.
CLASSIFY_TIMEOUT_SECONDS = 15.0
MAX_CATEGORIES_IN_PROMPT = 50


def _build_prompt(merchant_name: str, categories: list[tuple[int, str]]) -> str:
    listing = "\n".join(f"{cid}: {name}" for cid, name in categories)
    return (
        "Bạn là trợ lý phân loại chi tiêu cá nhân. Cho tên cửa hàng/đơn vị bán "
        "và danh sách danh mục (id: tên), hãy chọn ĐÚNG MỘT danh mục phù hợp "
        "nhất.\n\n"
        "Lưu ý phân biệt:\n"
        '- "Thực phẩm & siêu thị": siêu thị, cửa hàng tiện lợi, tạp hóa, hàng '
        "tiêu dùng thiết yếu (WinMart, Co.opmart, Bách Hóa Xanh, mart, siêu "
        "thị, cửa hàng tiện lợi).\n"
        '- "Mua sắm": thời trang, đồ điện tử, đồ gia dụng, bán lẻ không phải '
        "thực phẩm (Canifa, Uniqlo, Miniso, shop quần áo).\n\n"
        f"Tên cửa hàng: {merchant_name}\n\n"
        f"Danh sách danh mục:\n{listing}\n\n"
        'Trả về DUY NHẤT JSON dạng {"category_id": <id>} với id nằm trong danh '
        'sách trên. Nếu không chắc chắn hoặc không có danh mục nào phù hợp, trả '
        '{"category_id": null}. Không thêm giải thích, không markdown.'
    )


def _parse_category_id(content: str, valid_ids: set[int]) -> int | None:
    """Parse LLM content -> category_id hợp lệ hoặc None.

    Chống bịa: chỉ chấp nhận id nằm trong `valid_ids`.
    """
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: tìm số đầu tiên trong chuỗi.
        match = re.search(r"-?\d+", text)
        if match is None:
            return None
        candidate = int(match.group())
        return candidate if candidate in valid_ids else None

    # LLM trả số trần (vd "3") → json.loads ra int, không phải dict.
    if isinstance(data, int):
        return data if data in valid_ids else None

    if not isinstance(data, dict):
        return None
    raw = data.get("category_id")
    if raw is None:
        return None
    try:
        candidate = int(raw)
    except (TypeError, ValueError):
        return None
    return candidate if candidate in valid_ids else None


def classify_merchant_category(
    merchant_name: str,
    categories: list[tuple[int, str]],
) -> int | None:
    """Gọi LLM phân loại merchant vào 1 category trong `categories`.

    Args:
        merchant_name: tên cửa hàng (đã trim).
        categories: list (category_id, name) khả dụng cho user.

    Returns:
        category_id được chọn (nằm trong danh sách) hoặc None nếu không
        phân loại được / LLM tắt / lỗi.
    """
    if not merchant_name or not merchant_name.strip():
        return None
    if not categories:
        return None

    settings = get_settings()
    base_url = (settings.chat_llm_base_url or "").strip()
    api_key = (settings.chat_llm_api_key or "").strip()
    model = (settings.chat_llm_model or "").strip()
    if not (base_url and api_key and model):
        logger.info("category_classifier.llm_not_configured")
        return None

    # Giới hạn số category trong prompt để tránh prompt quá dài.
    bounded = categories[:MAX_CATEGORIES_IN_PROMPT]
    valid_ids = {cid for cid, _ in bounded}
    prompt = _build_prompt(merchant_name.strip(), bounded)

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
                "max_tokens": 30,
            },
            timeout=CLASSIFY_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            logger.warning(
                "category_classifier.llm_http_error status=%d body=%s",
                response.status_code,
                response.text[:200],
            )
            return None
        data = response.json()
        content = data["choices"][0]["message"].get("content", "") or ""
    except Exception as exc:  # noqa: BLE001 - fail-soft, không chặn luồng chính
        logger.warning("category_classifier.llm_failed error=%s", str(exc)[:200])
        return None

    category_id = _parse_category_id(content, valid_ids)
    logger.info(
        "category_classifier.result merchant=%s category_id=%s",
        merchant_name[:80],
        category_id,
    )
    return category_id


__all__ = ["classify_merchant_category"]
