# Requirements Document — AI Chatbot

## Introduction

Thay thế module "AI Insights" (one-shot batch generation, fix cứng output schema) bằng một
**chatbot conversational** cho phép người dùng hỏi đáp tự nhiên về chi tiêu cá nhân của mình.
Chatbot dùng LLM với function calling để gọi các query function trên backend, đảm bảo mọi
số liệu trả về đều đến từ database thực của user, không hallucinate.

### Lý do thay đổi
- Insight cũ quá rigid: user chỉ có 1 nút "Generate", nhận 3 array cố định.
- Không trả lời được câu hỏi cụ thể như "Tháng trước tôi tiêu bao nhiêu ở Grab?".
- Dataset MVP nhỏ, RAG chưa cần; function calling chính xác hơn cho structured data.
- LLM hiện tại (`cx/gpt-5.5` qua `http://localhost:20128/v1`) đã verify hỗ trợ function
  calling + streaming SSE + multi-turn tool result.

## Glossary

- **Chatbot**: giao diện hội thoại hỏi đáp chi tiêu.
- **Tool**: một function backend được expose cho LLM gọi qua function calling.
- **Tool Registry**: dict mapping tên tool → callable backend function.
- **Chat Turn**: một chu kỳ user message → LLM response (có thể gồm nhiều tool call vòng).
- **Chat History**: danh sách message tuần tự của 1 user, persist trong DB.
- **System Prompt**: prompt khởi động định nghĩa vai trò, ngôn ngữ, rules cho LLM.
- **Function Calling**: cơ chế OpenAI/tương thích cho phép LLM yêu cầu gọi function với args JSON.
- **SSE (Server-Sent Events)**: kênh streaming 1 chiều server → client để gửi token.

## Requirements

### Requirement 1: Bỏ module Insight cũ

**User Story:** Là developer, tôi muốn xóa sạch code insight cũ để tránh dead code và
giảm bảo trì, vì chatbot mới sẽ thay thế hoàn toàn chức năng này.

#### Acceptance Criteria
1. THE system SHALL xóa toàn bộ files trong `backend/api/app/services/insights/`.
2. THE system SHALL xóa `backend/api/app/api/v1/insights.py` và `schemas/insights.py`.
3. THE system SHALL xóa frontend `app/insights/` và `lib/insights-api.ts`.
4. THE system SHALL remove insights router mount trong `main.py`.
5. THE system SHALL tạo migration drop table `insight_snapshots`.
6. AFTER cleanup, backend ruff + mypy + pytest SHALL pass, frontend build SHALL pass.

### Requirement 2: Chat query service layer

**User Story:** Là developer, tôi muốn có các query function rõ ràng, testable, scoped theo
user_id, để LLM có thể gọi qua function calling mà không cần truy cập DB trực tiếp.

#### Acceptance Criteria
1. THE system SHALL expose tối thiểu 7 query functions: `query_spending_summary`,
   `search_transactions`, `get_budget_status`, `compare_periods`, `get_top_merchants`,
   `get_spending_by_day`, `get_recent_transactions`.
2. FOR ALL query functions, the first parameter SHALL be `user_id` và function SHALL chỉ
   trả về data thuộc về user đó.
3. THE query functions SHALL trả về dataclass hoặc dict serializable, không phải ORM object.
4. FOR ALL query functions, WHERE không có data matching, the function SHALL trả về empty
   collection hoặc None có ý nghĩa thay vì raise exception.
5. THE query functions SHALL tái sử dụng `compute_summary`, `compute_budget_usage`,
   `resolve_range` khi phù hợp thay vì duplicate logic.

### Requirement 3: LLM client OpenAI-compatible

**User Story:** Là developer, tôi muốn có client module tách biệt để gọi LLM, để dễ test
và thay provider sau này.

#### Acceptance Criteria
1. THE LLM client SHALL support endpoint `http://localhost:20128/v1` với model `cx/gpt-5.5`.
2. THE LLM client SHALL hỗ trợ function calling theo OpenAI Chat Completions spec.
3. THE LLM client SHALL hỗ trợ streaming mode với SSE chunks.
4. THE LLM client SHALL timeout sau 60 giây mặc định, có thể config.
5. THE LLM client SHALL retry 1 lần với backoff 1 giây cho network error, không retry cho
   4xx errors.
6. THE LLM client SHALL log request/response với API key redacted.

### Requirement 4: Chat orchestrator với multi-turn tool calling

**User Story:** Là developer, tôi muốn orchestrator xử lý hoàn chỉnh 1 chat turn: từ câu
hỏi user đến câu trả lời cuối, bao gồm nhiều vòng tool call nếu cần.

#### Acceptance Criteria
1. THE orchestrator SHALL load history gần nhất (tối đa 40 messages) trước khi gọi LLM.
2. THE orchestrator SHALL prepend system prompt tiếng Việt với rules an toàn.
3. WHEN LLM trả tool_calls, THE orchestrator SHALL execute từng tool và trả kết quả về LLM
   trong message tiếp theo với role=tool.
4. THE orchestrator SHALL cap tối đa 5 vòng tool call mỗi turn để tránh infinite loop.
5. THE orchestrator SHALL persist mọi message (user, assistant, tool) vào table
   `chat_messages` với `user_id` của người gửi.
6. THE orchestrator SHALL enforce `user_id` khi execute tool bất kể LLM có truyền user_id
   khác trong args hay không.
7. WHERE LLM response là text, the orchestrator SHALL stream chunks ra caller real-time.

### Requirement 5: Chat API endpoints

**User Story:** Là user, tôi muốn gửi câu hỏi và nhận câu trả lời streaming mượt, xem
được lịch sử chat, và có thể xóa lịch sử.

#### Acceptance Criteria
1. THE system SHALL expose `POST /api/v1/chat/message` với SSE response stream.
2. THE SSE stream SHALL emit events: `token` (text chunk), `tool_call` (đang gọi tool),
   `done` (hoàn tất), `error` (lỗi).
3. THE system SHALL expose `GET /api/v1/chat/history?limit=50&before_id=...` trả về
   ChatMessage list của user hiện tại, cursor-based pagination.
4. THE system SHALL expose `DELETE /api/v1/chat/history` xóa toàn bộ lịch sử của user.
5. ALL chat endpoints SHALL yêu cầu authentication (401 nếu không có session).
6. THE system SHALL rate limit 10 requests/phút/user cho POST /message (429 nếu vượt).

### Requirement 6: Chat persistence

**User Story:** Là user, tôi muốn xem lại toàn bộ lịch sử chat khi quay lại page, lịch sử
được lưu unlimited.

#### Acceptance Criteria
1. THE system SHALL tạo table `chat_messages` với cột: id, user_id, role, content,
   tool_calls_json, tool_call_id, tool_name, created_at.
2. THE `role` column SHALL accept values "user" | "assistant" | "tool".
3. THE table SHALL có index trên (user_id, created_at) để query history nhanh.
4. THE system SHALL không tự động xóa lịch sử (unlimited retention theo yêu cầu).
5. THE ChatMessage entity SHALL nằm trong `pfa_shared.entities` để API và worker dùng chung.

### Requirement 7: Frontend chat UI

**User Story:** Là user, tôi muốn gõ câu hỏi tự nhiên, thấy bot trả lời streaming mượt,
có gợi ý câu hỏi để bắt đầu, giao diện giống phần còn lại của app.

#### Acceptance Criteria
1. THE frontend SHALL expose route `/chat` thay thế route `/insights` cũ.
2. THE chat page SHALL hiển thị message bubbles phân biệt user (bên phải) và assistant (bên trái).
3. THE chat page SHALL stream text assistant từng chunk khi LLM trả về.
4. THE chat page SHALL hiển thị 4 suggested questions fixed khi chưa có message nào.
5. THE chat page SHALL load history cũ khi mount (gọi `GET /chat/history`).
6. THE chat UI SHALL match design tokens hiện tại (slate palette, rounded-md, Tailwind).
7. THE chat UI SHALL escape text để tránh XSS khi render content.
8. THE chat UI SHALL có empty state, loading state, streaming state, error state.
9. THE chat UI SHALL responsive mobile (full-width) và desktop (max-width ~720px centered).

### Requirement 8: Safety và user isolation

**User Story:** Là user, tôi muốn bot không trả lời các chủ đề ngoài scope chi tiêu, không
leak data người khác, và không bị manipulate bởi prompt injection.

#### Acceptance Criteria
1. THE orchestrator SHALL filter assistant response không được chứa banned phrases
   ("đầu tư chứng khoán", "cổ phiếu", "crypto", "bitcoin", "forex", "vay tiền nhanh",
   "lãi suất", "bảo hiểm nhân thọ", "tư vấn pháp lý", "tư vấn y tế").
2. IF assistant response chứa banned phrase, THE orchestrator SHALL thay bằng fallback
   message "Xin lỗi, mình chỉ hỗ trợ câu hỏi về chi tiêu cá nhân."
3. THE orchestrator SHALL luôn override bất kỳ user_id nào LLM truyền trong tool args bằng
   user_id của session hiện tại.
4. THE system prompt SHALL cấm LLM trả lời vượt scope chi tiêu cá nhân.
5. THE system SHALL không log câu hỏi/trả lời của user raw; chỉ log metadata (user_id,
   tool_calls_count, duration_ms).

### Requirement 9: Observability

**User Story:** Là developer, tôi muốn debug được khi chatbot lỗi hoặc chậm ở production.

#### Acceptance Criteria
1. FOR EACH chat turn, THE system SHALL log: user_id, message_length, tool_calls_count,
   duration_ms, status (success/error).
2. WHERE LLM response có field `usage`, THE system SHALL log prompt_tokens + completion_tokens.
3. THE system SHALL log error với stacktrace khi tool execution fail hoặc LLM timeout.

### Requirement 10: Exit criteria

**User Story:** Là product owner, tôi muốn Phase 6 chỉ được đóng khi chatbot thực sự dùng
được end-to-end.

#### Acceptance Criteria
1. User SHALL gửi câu hỏi tiếng Việt về chi tiêu và nhận câu trả lời với số liệu khớp DB.
2. THE chatbot SHALL handle được 5 loại câu hỏi phổ biến: tổng chi, so sánh kỳ, top
   merchant, budget status, search theo merchant.
3. Streaming SHALL đạt first token < 300ms trong điều kiện bình thường.
4. Chat history SHALL persist và load đúng khi user reload page.
5. Two users với cùng câu hỏi SHALL nhận 2 câu trả lời khác nhau từ data riêng của mỗi
   người; không leak data chéo.
6. Backend module `services/chat/` SHALL có test coverage > 80%.
