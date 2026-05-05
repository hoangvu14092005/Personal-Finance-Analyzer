"""GeminiInsightProvider stub (Phase 6.4).

Gọi Google Generative AI (Gemini) qua `google-generativeai` SDK.

Stub MVP: raise NotImplementedError để user biết cần setup API key +
install SDK trước khi dùng.

Setup:
1. `uv add google-generativeai` (chưa thêm dep MVP để giảm install size).
2. Lấy API key từ https://ai.google.dev.
3. Set env `INSIGHT_PROVIDER=gemini` + `GEMINI_API_KEY=...` +
   `GEMINI_MODEL=gemini-1.5-flash` (hoặc khác).
4. Uncomment body trong `generate()`.

Reference:
- https://ai.google.dev/gemini-api/docs/text-generation
"""
from __future__ import annotations

import json
from typing import ClassVar

from app.schemas.insights import InsightPayload
from app.services.insights.prompt import build_prompt
from app.services.insights.providers.base import (
    InsightProvider,
    InsightProviderError,
)
from app.services.insights.summary import SummaryInput


class GeminiInsightProvider(InsightProvider):
    name: ClassVar[str] = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-1.5-flash",
        timeout_seconds: float = 60.0,
    ) -> None:
        if not api_key:
            raise InsightProviderError("GEMINI_API_KEY phải được set.")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(self, summary: SummaryInput) -> InsightPayload:
        """Sinh InsightPayload qua Gemini. Hiện stub.

        Reference implementation:
        ```python
        import google.generativeai as genai
        from pydantic import ValidationError

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(
            self.model,
            generation_config={"response_mime_type": "application/json"},
        )

        prompt = build_prompt(summary)
        try:
            response = model.generate_content(prompt)
        except Exception as exc:  # SDK exceptions chung.
            raise InsightProviderError(f"Gemini request failed: {exc}") from exc

        raw = response.text
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InsightProviderError(
                f"Gemini response not JSON: {raw[:200]}",
            ) from exc
        try:
            return InsightPayload.model_validate(parsed)
        except ValidationError as exc:
            raise InsightProviderError(f"Schema validation failed: {exc}") from exc
        ```
        """
        _ = build_prompt
        _ = json
        raise InsightProviderError(
            "GeminiInsightProvider chưa được kích hoạt. Hướng dẫn setup:"
            " 1) `uv add google-generativeai`, 2) lấy API key từ"
            " https://ai.google.dev, 3) set INSIGHT_PROVIDER=gemini +"
            " GEMINI_API_KEY=..., 4) uncomment body trong"
            " app/services/insights/providers/gemini.py.",
        )


__all__ = ["GeminiInsightProvider"]
