"""AI Insights service layer (Phase 6).

Package structure:
- `summary`: build deterministic input dict từ analytics + budgets + anomaly.
- `eligibility`: check đủ dữ liệu để generate (min transactions, min days).
- `providers/`: adapter pattern (Mock/Ollama/Gemini).
- `prompt`: prompt builder với domain rules.
- `safety`: grounding checks cho output của provider.
- `generator`: orchestrate pipeline + cache lookup + persist snapshot.
"""
from __future__ import annotations
