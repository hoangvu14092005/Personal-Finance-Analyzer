"""InsightProvider abstraction (Phase 6.4).

Provider adapters phải implement protocol `InsightProvider`:
- `name`: identifier ngắn (vd "mock", "ollama", "gemini").
- `generate(summary: SummaryInput) -> InsightPayload`: sync, raise
  `InsightProviderError` khi fail hoặc không parse được output.

Concrete providers:
- `MockInsightProvider`: rule-based, không gọi LLM thật. Dùng cho MVP +
  test + dev khi chưa setup Ollama/Gemini.
- `OllamaInsightProvider`: gọi `http://localhost:11434/api/generate` với
  model llama3.2 (hoặc khác) — stub sẵn, cần user setup Ollama.
- `GeminiInsightProvider`: gọi Google Generative AI API — stub sẵn, cần
  API key.

Mỗi provider TỰ:
1. Build prompt (dùng `services.insights.prompt.build_prompt`).
2. Gọi LLM (hoặc sinh output rule-based với Mock).
3. Parse output JSON → `InsightPayload` (Pydantic validate).
4. Raise `InsightProviderError` nếu thất bại ở bất kỳ bước nào.

Caller (`services.insights.generator`) chịu trách nhiệm:
- Chạy safety/grounding checks trên output.
- Persist snapshot.
- Cache theo fingerprint.
"""
from __future__ import annotations

from typing import ClassVar, Protocol, runtime_checkable

from app.schemas.insights import InsightPayload
from app.services.insights.summary import SummaryInput


class InsightProviderError(Exception):
    """Raise khi provider không sinh được output hợp lệ."""


@runtime_checkable
class InsightProvider(Protocol):
    """Provider interface — adapter pattern cho LLM backends.

    `name` là class-level identifier ngắn (vd. "mock"). Dùng `ClassVar`
    để concrete providers có thể khai báo bằng `name: ClassVar[str] = "mock"`
    mà không bị mypy coi là override instance attribute.
    """

    name: ClassVar[str]

    def generate(self, summary: SummaryInput) -> InsightPayload:
        """Sinh `InsightPayload` từ summary input.

        Raises:
            InsightProviderError: khi LLM lỗi, output không parse được,
                hoặc vi phạm schema constraints.
        """
        ...


__all__ = ["InsightProvider", "InsightProviderError"]
