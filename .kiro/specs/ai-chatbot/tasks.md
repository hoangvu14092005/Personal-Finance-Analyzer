# Implementation Tasks — AI Chatbot

Kế hoạch chi tiết từng task để chuyển từ "AI Insights" (one-shot) sang "AI Chatbot"
(conversational). Mỗi task có entry/exit criteria rõ ràng, ưu tiên làm theo thứ tự số.

## Pre-requisites
- LLM endpoint verified: `http://localhost:20128/v1` model `cx/gpt-5.5` (function calling + streaming OK).
- Current phase 5 (budgets) complete; phase 6 insight cũ đã deploy.

---

## Task 6.0 — Cleanup module Insight cũ

**Goal**: Xóa sạch dead code để tránh nhầm lẫn khi build chatbot.

### Steps
1. Delete files:
   - `backend/api/app/services/insights/` (entire folder)
   - `backend/api/app/api/v1/insights.py`
   - `backend/api/app/schemas/insights.py`
   - `frontend/web/app/insights/` (entire folder)
   - `frontend/web/lib/insights-api.ts`
2. Remove imports/mounts:
   - `backend/api/app/main.py`: remove `from app.api.v1.insights import router as insights_router` và `app.include_router(insights_router, ...)`.
   - Frontend nav link `/insights` trong `app/layout.tsx`.
3. Migration Alembic:
   - Generate `drop_insight_snapshots` migration.
   - Test up/down.
4. Cập nhật `pfa_shared/entities.py`: remove `InsightSnapshot` class và export.
5. Grep check: `grep -r "insight" backend/ frontend/` → không còn reference ngoài docs.

### Validation
- `ruff check app tests` + `mypy app` + `pytest -q` pass.
- `pnpm lint` + `pnpm build` pass.
- Alembic migration apply sạch.

### Ước tính
0.5 ngày.

---

## Task 6.1 — Chat query service layer

**Goal**: Viết 7 query function để LLM gọi qua function calling.

### Steps
1. Tạo `backend/api/app/services/chat/__init__.py` và `queries.py`.
2. Định nghĩa dataclasses return type:
   ```python
   @dataclass(frozen=True, slots=True)
   class SpendingSummaryResult:
       total_spend: Decimal
       transaction_count: int
       top_categories: list[CategoryBreakdown]
       date_range: DateRange
   ```
3. Implement 7 functions:
   - `query_spending_summary(session, user_id, date_range_preset, category_name=None)` — tái sử dụng `compute_summary`.
   - `search_transactions(session, user_id, *, merchant=None, date_range_preset=None, amount_min=None, amount_max=None, category_name=None, limit=20)`.
   - `get_budget_status(session, user_id, period_month=None)` — default `period_month = current month`, wrap `compute_budget_usage`.
   - `compare_periods(session, user_id, period_a_preset, period_b_preset)` — 2 `compute_summary` calls.
   - `get_top_merchants(session, user_id, date_range_preset, limit=10)` — GROUP BY merchant_name.
   - `get_spending_by_day(session, user_id, date_range_preset)` — GROUP BY transaction_date.
   - `get_recent_transactions(session, user_id, limit=10)` — ORDER BY date DESC, id DESC.
4. Mỗi function:
   - Nhận `user_id` là param bắt buộc đầu tiên (sau `session`).
   - Filter `WHERE user_id = user_id` trong query SQL.
   - Trả về empty list hoặc None có ý nghĩa khi không có data.
   - Docstring mô tả ngắn gọn cho LLM description.
5. Escape LIKE wildcard cho merchant search (fix bug hiện có):
   ```python
   escaped = merchant.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
   ```

### Tests
- `backend/api/tests/test_chat_queries.py`
- Mỗi function: 2-3 test case (happy, empty, cross-user isolation).
- Cross-user isolation: seed 2 users, query user A không được thấy data user B.

### Validation
- `pytest tests/test_chat_queries.py -v` pass.
- Coverage > 90% cho `queries.py`.

### Ước tính
1-1.5 ngày.

---

## Task 6.2 — LLM client OpenAI-compatible

**Goal**: HTTP client tái sử dụng cho chat + future features.

### Steps
1. Tạo `backend/api/app/services/chat/llm_client.py`.
2. Class `OpenAICompatClient`:
   - `__init__(base_url, api_key, model, timeout_seconds=60)`.
   - `async chat(messages, tools=None, stream=False, tool_choice="auto") -> dict | AsyncIterator[dict]`.
   - `async close()`.
3. Implement:
   - Sync mode: `POST /chat/completions` + return JSON response.
   - Stream mode: `POST /chat/completions` với `stream=True` body + parse SSE chunks → yield parsed delta dicts.
4. Retry logic: 1 retry với backoff 1s cho `httpx.NetworkError` và `httpx.TimeoutException`. Không retry 4xx.
5. Logging:
   - Log `llm.request_start` với model, message_count, has_tools.
   - Log `llm.request_end` với duration_ms, status, tokens_used (từ response.usage nếu có).
   - Không log full messages (privacy); log length thay vì content.
   - Redact `Authorization` header trong log.
6. Config settings:
   ```python
   # app/core/config.py
   chat_llm_base_url: str = "http://localhost:20128/v1"
   chat_llm_api_key: str = ""
   chat_llm_model: str = "cx/gpt-5.5"
   chat_llm_timeout_seconds: float = 60.0
   ```
7. Fail-fast validator: staging/prod yêu cầu `chat_llm_api_key != ""`.

### Tests
- `test_llm_client.py` dùng `httpx.MockTransport`:
  - Verify payload format đúng OpenAI spec.
  - Test function calling request/response.
  - Test stream parse SSE chunks đúng.
  - Test timeout raise exception.
  - Test retry logic.

### Validation
- `pytest tests/test_llm_client.py -v` pass.
- Manual test: gọi LLM thật, log đủ thông tin.

### Ước tính
0.5-1 ngày.

---

## Task 6.3 — Chat persistence (entity + migration)

**Goal**: Table `chat_messages` + `ChatMessage` entity shared.

### Steps
1. Thêm `ChatMessage` vào `backend/shared/pfa_shared/entities.py` (xem design.md).
2. Export trong `__all__`.
3. Alembic migration:
   - Drop `insight_snapshots` (nếu chưa làm ở task 6.0).
   - Create `chat_messages` với các cột + index `(user_id, created_at)`.
4. Re-export trong `backend/api/app/models/entities.py` (thin shim pattern như User, Transaction).
5. Test migration up/down reversible trên SQLite + PostgreSQL.

### Validation
- `alembic upgrade head` rồi `alembic downgrade -1` rồi `upgrade head` đều pass.
- `SELECT COUNT(*) FROM chat_messages` trả 0 sau migration.
- Mypy pass.

### Ước tính
0.5 ngày.

---

## Task 6.4 — Tool registry + schemas

**Goal**: Map query functions → OpenAI tool definitions.

### Steps
1. Tạo `backend/api/app/services/chat/tools.py`.
2. Định nghĩa `ToolDefinition` dataclass.
3. Build `TOOL_REGISTRY` với 7 entries (xem design.md).
4. Parameters JSON Schema cho mỗi tool:
   - Dùng enum cho `date_range` ("7d", "30d", "this_month", "last_month").
   - Optional params có default null.
   - Description tiếng Anh ngắn gọn (LLM hiểu tốt hơn tiếng Việt cho schema).
5. Function `get_openai_tools() -> list[dict]` format đúng OpenAI spec.
6. Function `execute_tool(name, user_id, args) -> dict`:
   - Validate name tồn tại.
   - **Strip `user_id` khỏi args** (defense: LLM có thể truyền nhầm/cố ý).
   - Call handler với `user_id` được set từ session.
   - Catch exception, return `{"error": "...message..."}` để LLM biết fail gracefully.
7. Serialize result: Decimal → str, date → ISO string, dataclass → asdict.

### Tests
- `test_tools.py`:
  - Verify mỗi tool có schema hợp lệ (JSON Schema validator).
  - Test `execute_tool` dispatch đúng handler.
  - Test `user_id` override: LLM truyền user_id=999, phải bị ignore, thực tế dùng user_id=5 từ caller.

### Validation
- Tất cả 7 tools có schema render được qua JSON Schema validator.
- Test pass.

### Ước tính
0.5-1 ngày.

---

## Task 6.5 — Chat orchestrator

**Goal**: Multi-turn loop với tool calling + streaming.

### Steps
1. Tạo `backend/api/app/services/chat/system_prompt.py` với `SYSTEM_PROMPT` tiếng Việt.
2. Tạo `backend/api/app/services/chat/orchestrator.py`.
3. Helper functions:
   - `_load_recent_history(session, user_id, limit) -> list[ChatMessage]`
   - `_history_to_openai_format(history) -> list[dict]`
   - `_persist_user_message(session, user_id, content)`
   - `_persist_assistant_message(session, user_id, content, tool_calls=None)`
   - `_persist_tool_result(session, user_id, tool_call_id, tool_name, content)`
4. Main function `run_chat_turn(session, llm, user_id, user_message) -> AsyncIterator[ChatStreamEvent]`:
   - Guard: max 5 tool rounds, max 40 history messages.
   - Persist user message first.
   - Loop: call LLM → if tool_calls, execute + persist + append + continue; if content, stream.
   - For final text streaming: call `llm.chat(..., stream=True)` và yield tokens.
   - Apply safety filter (banned phrases) trên final content trước khi persist.
5. Define `ChatStreamEvent` dataclass.
6. Error handling:
   - LLM timeout → yield error event + persist assistant message "Xin lỗi, hệ thống bận, thử lại."
   - Tool exception → append error as tool result, LLM tự fallback.
   - Max rounds exceeded → yield error event.

### Tests
- `test_orchestrator.py`:
  - Mock LLM client (fake responses).
  - Scenario 1: LLM trả content ngay (no tool call) → 1 round, stream tokens, persist msgs.
  - Scenario 2: 1 tool call → execute → LLM trả content → 2 rounds.
  - Scenario 3: 2 tool calls liên tiếp → 3 rounds total.
  - Test max rounds: LLM luôn trả tool_call → error after 5 rounds.
  - Test user_id override: LLM truyền user_id khác trong args → vẫn dùng session user_id.
  - Test cross-user: history chỉ load của user hiện tại.

### Validation
- Pytest pass tất cả scenarios.
- Manual test với LLM thật: hỏi câu đơn giản → bot trả lời đúng.

### Ước tính
1.5-2 ngày.

---

## Task 6.6 — Safety layer + rate limit

**Goal**: Filter banned phrases + rate limit per user.

### Steps
1. Tạo `backend/api/app/services/chat/safety.py`.
2. `BANNED_PHRASES` tuple (tái sử dụng từ insight cũ đã xóa, port sang).
3. Function `apply_safety_filter(content: str) -> str`:
   - Nếu content chứa banned phrase (case-insensitive substring) → return fallback.
4. Rate limiter đơn giản in-memory:
   ```python
   from collections import defaultdict
   from time import monotonic

   _BUCKETS: dict[int, list[float]] = defaultdict(list)

   def check_rate_limit(user_id: int, max_per_minute: int = 10) -> None:
       now = monotonic()
       bucket = _BUCKETS[user_id]
       # Remove timestamps older than 60s
       bucket[:] = [t for t in bucket if now - t < 60]
       if len(bucket) >= max_per_minute:
           raise RateLimitExceeded()
       bucket.append(now)
   ```
5. Integrate: gọi `check_rate_limit` trong API endpoint, `apply_safety_filter` trong orchestrator.

### Tests
- Test banned phrase detection + replacement.
- Test rate limit: 10 calls → OK, lần 11 → raise.
- Test bucket cleanup sau 60s (monkeypatch monotonic).

### Ước tính
0.5 ngày.

---

## Task 6.7 — Chat API endpoints (SSE)

**Goal**: Expose HTTP endpoints cho frontend.

### Steps
1. Tạo `backend/api/app/schemas/chat.py`:
   - `ChatMessageRequest` (content).
   - `ChatMessageItem` (id, role, content, tool_calls, tool_name, created_at).
   - `ChatHistoryResponse` (items, has_more, next_before_id).
2. Tạo `backend/api/app/api/v1/chat.py`:
   - `POST /chat/message` — StreamingResponse SSE (xem design.md).
   - `GET /chat/history?limit=50&before_id=...` — cursor pagination.
   - `DELETE /chat/history` — 204 No Content.
3. Mount router trong `main.py`.
4. SSE format:
   ```
   event: token
   data: {"content": "Tháng này "}

   event: tool_call
   data: {"name": "search_transactions"}

   event: done
   data: {}
   ```
5. Content-Type: `text/event-stream`, headers anti-buffer (`X-Accel-Buffering: no`).

### Tests
- `test_chat_api.py`:
  - POST /message với mocked LLM → collect stream → verify events.
  - GET /history pagination forward.
  - DELETE /history rồi GET → empty.
  - 401 unauth, 429 rate limit, 503 LLM down.

### Ước tính
1 ngày.

---

## Task 6.8 — Frontend chat UI

**Goal**: Trang `/chat` thay thế `/insights`.

### Steps
1. Tạo `frontend/web/app/chat/page.tsx` + `chat-client.tsx`.
2. Components:
   - `message-bubble.tsx` (user right, assistant left, escape XSS).
   - `suggested-questions.tsx` (4 prompts fixed: "Tổng chi tháng này", "So với tháng trước", "Top merchant tuần này", "Budget còn bao nhiêu").
   - `input-bar.tsx` (textarea + send button + Enter to send, Shift+Enter newline).
3. `lib/chat-api.ts`:
   - `sendMessage(content, handlers)` — fetch + ReadableStream + SSE parse.
   - `getHistory(beforeId?)` → list.
   - `clearHistory()`.
4. State management trong `chat-client.tsx`:
   - `messages: ChatMessageItem[]`.
   - `streaming: boolean`.
   - `error: string | null`.
   - On mount: load history, scroll to bottom.
   - On send: append user msg, append empty assistant, on token → update last assistant content, on done → lock.
5. Styles (match Tailwind tokens hiện tại):
   - User bubble: `bg-slate-900 text-white rounded-lg px-4 py-3`.
   - Assistant bubble: `bg-white border border-slate-200 rounded-lg px-4 py-3`.
   - Container: `max-w-2xl mx-auto`.
   - Mobile: full-width với padding.
6. Auth gate: `getMe()` → redirect login nếu fail (pattern giống pages khác).
7. Markdown light cho assistant: support `**bold**` và bullet list (regex replace, không dùng lib lớn).
8. Nav link: đổi `/insights` → `/chat` (icon 💬 "Trợ lý").

### Tests
- Playwright e2e (`e2e/chat.spec.ts`):
  - Login → navigate /chat → gõ "Tổng chi tháng này" → verify streaming → verify response chứa số từ DB thực.
  - Click suggested question → verify sends.
  - Clear history → refresh → verify empty.

### Validation
- `pnpm lint` + `tsc --noEmit` pass.
- `pnpm build` pass.
- Manual: chat mượt, scroll bottom auto, mobile responsive.

### Ước tính
2-3 ngày.

---

## Task 6.9 — Observability + docs

**Goal**: Log đủ thông tin debug + update docs.

### Steps
1. Log trong orchestrator: mỗi turn log:
   - `chat.turn_start user_id=X msg_len=Y`.
   - `chat.tool_executed name=Z duration_ms=N`.
   - `chat.turn_end user_id=X rounds=N tokens_used=T duration_ms=D status=ok`.
2. Log LLM token usage nếu có trong response (prompt_tokens + completion_tokens).
3. Update `progress_log.md` sau mỗi task hoàn thành.
4. Update `README.md` với section "AI Chatbot" (setup LLM endpoint env vars).
5. Update `.env.example` API + worker với chat settings.

### Ước tính
0.5 ngày.

---

## Task 6.10 — (Optional) RAG cho receipt text

**Goal**: Cho phép hỏi về nội dung receipt cụ thể.

**Defer nếu**: MVP chưa cần, user chưa feedback.

### Steps
1. Install `pgvector` extension PostgreSQL.
2. Migration: thêm cột `ocr_results.embedding VECTOR(1536)`.
3. Khi worker process OCR xong → call embedding API (có thể gọi `/v1/embeddings` trên LLM endpoint nếu support; nếu không → dùng local model qua ollama).
4. Tool mới: `search_receipt_text(user_id, query, limit=5) -> list[ReceiptMatch]`.
5. Register vào TOOL_REGISTRY.

### Ước tính
1-2 ngày (defer).

---

## Exit criteria Phase 6

- [x] 6.0: Dead code xóa, tests pass.
- [ ] 6.1: 7 query functions + coverage > 90%.
- [ ] 6.2: LLM client + tests + manual verify.
- [ ] 6.3: Entity + migration reversible.
- [ ] 6.4: Tool registry + user_id override test.
- [ ] 6.5: Orchestrator 3 scenarios pass.
- [ ] 6.6: Safety + rate limit tests.
- [ ] 6.7: API SSE end-to-end test.
- [ ] 6.8: Frontend UI + Playwright pass.
- [ ] 6.9: Logs + docs updated.

**Final acceptance**: 10 câu hỏi sample (xem design.md) trả lời đúng, không hallucinate,
không leak data giữa users, streaming mượt.

---

## Tổng thời gian ước tính
- Core (6.0-6.9): **6-9 ngày làm việc**.
- Với buffer testing + polish: **2 tuần**.
