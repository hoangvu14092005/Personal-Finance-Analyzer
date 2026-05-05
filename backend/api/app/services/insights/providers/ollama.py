"""OllamaInsightProvider stub (Phase 6.4).

Gọi Ollama local server qua `http://localhost:11434/api/generate` với
model như llama3.2, mistral, ...

Stub MVP: raise NotImplementedError để user biết cần setup trước khi
dùng. Code đầy đủ để user hoàn thiện khi sẵn sàng:

1. Pull model: `ollama pull llama3.2`.
2. Chạy server: `ollama serve`.
3. Set env `INSIGHT_PROVIDER=ollama` + `OLLAMA_URL=http://localhost:11434`
   + `OLLAMA_MODEL=llama3.2`.
4. Uncomment body trong `generate()`.

Request format Ollama:
```json
POST /api/generate
{
  "model": "llama3.2",
  "prompt": "<prompt>",
  "stream": false,
  "format": "json"
}
```

Response: `{"response": "<JSON string>"}`.
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


class OllamaInsightProvider(InsightProvider):
    name: ClassVar[str] = "ollama"

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(self, summary: SummaryInput) -> InsightPayload:
        """Sinh InsightPayload qua Ollama. Hiện stub — implement khi cần.

        Reference implementation (uncomment + test khi setup):
        ```python
        import httpx

        prompt = build_prompt(summary)
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise InsightProviderError(f"Ollama request failed: {exc}") from exc

        raw = response.json().get("response", "")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InsightProviderError(
                f"Ollama response not JSON: {raw[:200]}",
            ) from exc
        try:
            return InsightPayload.model_validate(parsed)
        except ValidationError as exc:
            raise InsightProviderError(f"Schema validation failed: {exc}") from exc
        ```
        """
        # Giữ tham chiếu để tránh ruff F401 unused imports trong stub.
        _ = build_prompt
        _ = json
        raise InsightProviderError(
            "OllamaInsightProvider chưa được kích hoạt. Hướng dẫn setup:"
            " 1) `ollama pull llama3.2`, 2) `ollama serve`,"
            " 3) set INSIGHT_PROVIDER=ollama, 4) uncomment body trong"
            " app/services/insights/providers/ollama.py.",
        )


__all__ = ["OllamaInsightProvider"]
