"""Prompt builder cho insight generation (Phase 6.5).

Rules bám vào PRD:
- Không bịa dữ liệu: chỉ nói về số trong `summary_input`.
- Không investment advice (chứng khoán, crypto, forex, vay).
- Không claim ngoài scope (dự đoán tương lai, advice y tế/luật...).
- Output STRICT JSON theo schema `InsightPayload`.
- Viết bằng tiếng Việt, ngắn gọn, thực tế.

Prompt template dùng cho Ollama/Gemini. MockProvider KHÔNG dùng prompt
(rule-based). Nhưng expose để test prompt content hợp lý.
"""
from __future__ import annotations

import json
from decimal import Decimal

from app.schemas.insights import (
    MAX_ALERTS,
    MAX_BODY_LEN,
    MAX_INSIGHTS,
    MAX_RECOMMENDATIONS,
    MAX_TITLE_LEN,
)
from app.services.insights.summary import SummaryInput

SYSTEM_RULES = f"""Bạn là trợ lý phân tích chi tiêu cá nhân cho người dùng Việt Nam. Nhiệm vụ:
dựa trên dữ liệu chi tiêu JSON (đã cung cấp) sinh ra `insights`, `recommendations`
và `alerts` để giúp user hiểu thói quen và kiểm soát ngân sách.

Các quy tắc BẮT BUỘC:
1. CHỈ dùng số và category name có trong JSON input. KHÔNG được tự tạo ra
   số liệu, tỷ lệ phần trăm, hay category không xuất hiện trong input.
2. KHÔNG đưa ra lời khuyên về đầu tư (chứng khoán, crypto, forex, vay nợ,
   bảo hiểm). Chỉ nói về quản lý chi tiêu hàng ngày.
3. KHÔNG dự đoán tương lai, không khuyến nghị y tế/luật pháp, không tạo
   nhận định cảm xúc tiêu cực (vd: "bạn tiêu quá nhiều", "lãng phí").
4. Output STRICT JSON đúng schema (sẽ mô tả bên dưới), KHÔNG có text
   ngoài JSON, KHÔNG có markdown code fence.
5. Viết tiếng Việt ngắn gọn, ≤ {MAX_TITLE_LEN} ký tự cho `title`, ≤ {MAX_BODY_LEN}
   ký tự cho `body`. Tối đa {MAX_INSIGHTS} insights, {MAX_RECOMMENDATIONS}
   recommendations, {MAX_ALERTS} alerts.
6. Nếu không đủ dữ liệu để ra insight chắc chắn, trả mảng rỗng.

Schema output:
```json
{{
  "insights": [
    {{"title": "<≤120 ký tự>", "body": "<≤400 ký tự>", "category_id": <int|null>}}
  ],
  "recommendations": [
    {{"title": "...", "body": "...", "estimated_savings": "<VND string|null>",
      "category_id": <int|null>}}
  ],
  "alerts": [
    {{"title": "...", "body": "...", "severity": "info|warning|critical",
      "category_id": <int|null>}}
  ]
}}
```
"""


def build_prompt(summary: SummaryInput) -> str:
    """Ghép system rules + JSON input → full prompt cho LLM.

    Gửi dạng 1 prompt đơn (không dùng chat history) để tương thích cả
    Ollama `/api/generate` và Gemini `generate_content`.
    """
    data = summary.to_dict()
    json_input = json.dumps(data, ensure_ascii=False, indent=2)
    return (
        f"{SYSTEM_RULES}\n\n"
        f"Dữ liệu chi tiêu (JSON):\n{json_input}\n\n"
        f"Trả về JSON hợp lệ theo schema trên, không có text khác."
    )


def format_vnd(amount: Decimal) -> str:
    """Helper format VND cho prompt examples. 1500000 → '1.500.000 VND'."""
    whole = int(amount)
    s = f"{whole:,}".replace(",", ".")
    return f"{s} VND"


__all__ = ["SYSTEM_RULES", "build_prompt", "format_vnd"]
