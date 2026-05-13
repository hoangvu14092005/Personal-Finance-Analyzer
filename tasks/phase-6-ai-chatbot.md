# Phase 6 - AI Chatbot (replaces Phase 6 - AI Insights)

> Quyết định kiến trúc: thay thế hoàn toàn "AI Insights" (one-shot batch generation) bằng
> chatbot conversational dùng function calling. Insight snapshot fix cứng không linh hoạt,
> UI user chỉ bấm 1 nút và nhận 3 array cố định (insights/recommendations/alerts).
> Chatbot cho phép hỏi đáp tự nhiên, query on-demand, tái sử dụng các service sẵn có.

## Outcome
Người dùng có một trợ lý hội thoại tiếng Việt, hiểu câu hỏi về chi tiêu cá nhân, tự động
gọi các tool backend để lấy đúng số liệu thực từ DB, trả lời chính xác không hallucinate.

## LLM Target
- Endpoint: `http://localhost:20128/v1` (OpenAI-compatible)
- Model: `cx/gpt-5.5`
- Đã verify: chat, function calling, streaming SSE, multi-turn tool result → answer.

## Nguyên tắc thiết kế
- Backend: tái sử dụng tối đa `analytics`, `budgets`, `date_ranges`, `category_suggestion`.
- Chỉ viết thêm các query function còn thiếu — không duplicate logic.
- LLM không bao giờ truy cập DB trực tiếp; luôn qua tool layer có `user_id` enforced.
- Response chatbot là text tự nhiên; không có structured cards phức tạp trong MVP.
- Chat history unlimited (theo yêu cầu user), persist vào PostgreSQL.

## Task breakdown

### 6.0 Cleanup module insight cũ
- Xóa:
  - `backend/api/app/services/insights/` (toàn bộ)
  - `backend/api/app/api/v1/insights.py`
  - `backend/api/app/schemas/insights.py`
  - `backend/api/app/main.py`: remove `insights_router` include
  - `frontend/web/app/insights/`
  - `frontend/web/lib/insights-api.ts`
  - Nav link `/insights` trong layout
- Giữ:
  - Entity `InsightSnapshot` tạm giữ (migration drop ở 6.3 khi table `chat_messages` ready)
  - Không giữ import reference nào đến các module đã xóa
- Acceptance: backend ruff/mypy/pytest pass; frontend build pass.

### 6.1 Chat query service layer
- File mới: `backend/api/app/services/chat/queries.py`
- Functions (tất cả nhận `user_id` bắt buộc, không bao giờ implicit):
  - `query_spending_summary(session, user_id, date_range, category_name?)` → tổng chi, count, top categories
  - `search_transactions(session, user_id, *, merchant?, date_range?, amount_min?, amount_max?, category_name?, limit=20)` → list transaction
  - `get_budget_status(session, user_id, period_month?)` → list budget usage (reuse `compute_budget_usage`)
  - `compare_periods(session, user_id, period_a, period_b)` → delta amount + percent
  - `get_top_merchants(session, user_id, date_range, limit=10)` → merchant ranking
  - `get_spending_by_day(session, user_id, date_range)` → daily breakdown
  - `get_recent_transactions(session, user_id, limit=10)` → latest N giao dịch
- Các function trả dataclass/dict serializable; không trả ORM object để LLM không nhận data thừa.
- Acceptance:
  - Unit test mỗi function với SQLite in-memory (tối thiểu 2 case: có data, không data).
  - Tất cả function filter đúng `user_id` — test case cross-user isolation.

### 6.2 LLM client (OpenAI-compatible)
- File mới: `backend/api/app/services/chat/llm_client.py`
- Lớp `OpenAICompatClient`:
  - `__init__(base_url, api_key, model, timeout)`
  - `chat(messages, tools=None, tool_choice="auto", stream=False)` → response dict hoặc async generator chunks
  - Dùng `httpx.AsyncClient`, retry 1 lần với backoff 1s cho lỗi network.
  - Log request/response (redact API key).
- Config settings thêm vào `app/core/config.py`:
  - `chat_llm_base_url: str = "http://localhost:20128/v1"`
  - `chat_llm_api_key: str = ""` (fail-fast prod nếu rỗng)
  - `chat_llm_model: str = "cx/gpt-5.5"`
  - `chat_llm_timeout_seconds: float = 60.0`
  - `chat_max_history_messages: int = 40` (context window guard)
- Acceptance:
  - Unit test với httpx `MockTransport` — verify payload đúng format OpenAI spec (messages, tools, tool_choice).
  - Test stream parse SSE chunks đúng.

### 6.3 Chat persistence
- Migration Alembic mới:
  - Drop `insight_snapshots` table (không còn dùng).
  - Create `chat_messages`:
    - `id` PK
    - `user_id` FK users.id, index
    - `role` enum: "user" | "assistant" | "tool"
    - `content` TEXT nullable (null cho assistant-with-tool-calls-only)
    - `tool_calls_json` TEXT nullable (JSON array OpenAI format)
    - `tool_call_id` VARCHAR(100) nullable (khi role=tool)
    - `tool_name` VARCHAR(100) nullable
    - `created_at` TIMESTAMPTZ default now, index
- Entity `ChatMessage` trong `pfa_shared/entities.py`.
- Acceptance:
  - Migration up/down reversible.
  - Entity import được cả API và worker (tương thích pattern M5).

### 6.4 Chat orchestrator
- File mới: `backend/api/app/services/chat/orchestrator.py`
- Core function `run_chat_turn(session, user_id, user_message) -> AsyncIterator[ChatStreamEvent]`:
  1. Load history cho user (limit 40 messages gần nhất).
  2. Prepend system prompt (tiếng Việt, rules an toàn, danh sách tools).
  3. Append user message, persist vào DB.
  4. Loop:
     - Call LLM với tools + stream.
     - Nếu có `tool_calls` trong response: execute từng tool sequentially (`TOOL_REGISTRY[name](user_id, **args)`), persist tool result message, tiếp tục loop.
     - Nếu có `content` (text): stream chunks ra caller, persist assistant message khi xong.
     - Max 5 tool-call rounds để tránh loop vô hạn.
- Tool schema definitions (OpenAI JSON Schema format) cho 7 functions ở 6.1.
- System prompt rules:
  - Trả lời tiếng Việt, ngắn gọn, dùng dấu phân cách thousand VN ("1.500.000 VND").
  - Chỉ dùng số liệu từ tool result, không đoán.
  - Không advice đầu tư/vay/bảo hiểm/y tế/luật.
  - Khi user hỏi vượt scope chi tiêu cá nhân → trả lời lịch sự rằng không phải chức năng của bạn.
- Acceptance:
  - Integration test với LLM client mocked: 3 scenarios — no-tool-call, single-tool-call, multi-tool-call.
  - Test max rounds guard.
  - Test user isolation: tool execute với đúng user_id dù LLM có cố "inject" ID khác trong args.

### 6.5 Chat API endpoints
- File mới: `backend/api/app/api/v1/chat.py`
- Endpoints:
  - `POST /api/v1/chat/message` (SSE):
    - Body: `{"content": "string"}`
    - Response: SSE stream với events: `token` (chunk text), `tool_call` (tool đang chạy), `done` (hoàn thành), `error`.
  - `GET /api/v1/chat/history?limit=50&before_id=...`:
    - Trả list ChatMessage của user, pagination cursor-based.
  - `DELETE /api/v1/chat/history`:
    - Xóa toàn bộ lịch sử của user (có confirm ở frontend).
- Schemas: `ChatMessageRequest`, `ChatMessageResponse`, `ChatHistoryResponse`.
- Acceptance:
  - 4xx/5xx mapping: 401 unauth, 429 rate limit (implement simple token bucket in-memory, 10 req/min/user), 503 LLM down.
  - SSE end-to-end test với TestClient.

### 6.6 Frontend chat UI
- Thay `/insights` page (đã xóa ở 6.0):
  - Route mới: `/chat`
  - Nav link: "Trợ lý" (icon 💬)
- Components:
  - `app/chat/chat-client.tsx`: main component, manage messages state + streaming.
  - `app/chat/message-bubble.tsx`: render user/assistant bubble, markdown light (bold, list).
  - `app/chat/suggested-questions.tsx`: 4 quick prompts fixed cho MVP.
  - `app/chat/input-bar.tsx`: textarea + send button + Enter shortcut.
- `lib/chat-api.ts`:
  - `sendMessage(content, onToken, onDone, onError)` dùng `EventSource` API (auth qua cookie SSE-compatible).
  - `getHistory(before_id?)` pagination.
  - `clearHistory()`.
- Styling: match design tokens hiện tại (slate palette, rounded-md, Tailwind).
- States: empty (chưa có message), loading history, streaming (bot đang gõ), error, offline (LLM 503).
- Acceptance:
  - Playwright e2e: gõ câu hỏi → thấy streaming → thấy câu trả lời có số liệu thực.
  - Mobile responsive.
  - Không XSS (escape text trong bubble).

### 6.7 Safety layer (tái sử dụng)
- Port `BANNED_PHRASES` check từ `safety.py` cũ (đã xóa) vào `chat/orchestrator.py`:
  - Pre-send: check user message không chứa prompt injection cơ bản ("ignore previous", v.v.).
  - Post-receive: check assistant content không chứa banned phrases → nếu có, replace bằng fallback message.
- Rate limit: 10 req/phút/user (simple in-memory dict + timestamp, reset mỗi phút).
- Acceptance:
  - Unit test banned phrase filter.
  - Rate limit test với fake time.

### 6.8 Observability
- Log mỗi chat turn: `user_id`, `tool_calls_count`, `tokens_used` (nếu LLM trả usage), `duration_ms`.
- Metric đơn giản (in log): số turn/day, tool call distribution.
- Acceptance: log đủ thông tin để debug production issue.

### 6.9 (Optional, defer) RAG cho receipt text
- Chỉ làm nếu user hỏi về nội dung receipt cụ thể ("Hóa đơn Grab ngày X có gì?").
- pgvector extension + embed OCR raw_text khi receipt processed.
- Tool mới: `search_receipt_text(user_id, query, limit=5)`.
- Defer sang post-MVP vì MVP không critical.

## Exit criteria Phase 6
- User gửi câu hỏi tiếng Việt về chi tiêu → chatbot trả lời với số liệu thực từ DB.
- Function calling hoạt động cho ≥ 5 loại câu hỏi phổ biến.
- Chat history persist + hiển thị đầy đủ khi quay lại page.
- Streaming hoạt động mượt (< 300ms first token).
- Không hallucinate số liệu (manual kiểm chứng 10 câu hỏi sample).
- Không leak data giữa users.
- Backend coverage > 80% cho module `services/chat/`.

## Ước tính
- 6.0: 0.5 ngày (cleanup)
- 6.1: 1-1.5 ngày (query functions + tests)
- 6.2: 0.5 ngày (LLM client)
- 6.3: 0.5 ngày (migration + entity)
- 6.4: 1-1.5 ngày (orchestrator + tests)
- 6.5: 0.5-1 ngày (API + SSE)
- 6.6: 2-3 ngày (frontend UI)
- 6.7-6.8: 0.5 ngày (safety + logs)
- Tổng: 6-9 ngày làm việc.
