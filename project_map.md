## Tổng quan kiến trúc thư mục đề xuất

```text
personal-finance-analyzer/
├─ frontend/
│  ├─ web/
│  │  ├─ app/
│  │  │  ├─ (auth)/
│  │  │  ├─ (dashboard)/
│  │  │  ├─ receipts/
│  │  │  ├─ transactions/
│  │  │  ├─ budgets/
│  │  │  ├─ chat/
│  │  │  ├─ settings/
│  │  │  ├─ layout.tsx
│  │  │  ├─ page.tsx
│  │  │  └─ globals.css
│  │  ├─ components/
│  │  │  ├─ ui/
│  │  │  ├─ forms/
│  │  │  ├─ charts/
│  │  │  ├─ layout/
│  │  │  └─ domain/
│  │  ├─ features/
│  │  │  ├─ auth/
│  │  │  ├─ receipts/
│  │  │  ├─ transactions/
│  │  │  ├─ dashboard/
│  │  │  ├─ budgets/
│  │  │  └─ chat/
│  │  ├─ lib/
│  │  │  ├─ api/
│  │  │  ├─ hooks/
│  │  │  ├─ utils/
│  │  │  ├─ config/
│  │  │  └─ query/
│  │  ├─ providers/
│  │  ├─ styles/
│  │  ├─ types/
│  │  ├─ public/
│  │  ├─ tests/
│  │  ├─ package.json
│  │  └─ tsconfig.json
│  └─ docs/
│     ├─ ui-flows/
│     └─ design-notes/
├─ backend/
│  ├─ api/
│  │  ├─ app/
│  │  │  ├─ api/
│  │  │  │  ├─ v1/
│  │  │  │  │  ├─ auth.py
│  │  │  │  │  ├─ receipts.py
│  │  │  │  │  ├─ transactions.py
│  │  │  │  │  ├─ dashboard.py
│  │  │  │  │  ├─ budgets.py
│  │  │  │  │  └─ chat.py
│  │  │  ├─ core/
│  │  │  │  ├─ config.py
│  │  │  │  ├─ security.py
│  │  │  │  ├─ database.py
│  │  │  │  ├─ cache.py
│  │  │  │  └─ logging.py
│  │  │  ├─ models/
│  │  │  ├─ schemas/
│  │  │  ├─ services/
│  │  │  ├─ repositories/
│  │  │  ├─ domain/
│  │  │  ├─ integrations/
│  │  │  │  ├─ storage/
│  │  │  │  ├─ ocr/
│  │  │  │  └─ llm/
│  │  │  ├─ dependencies/
│  │  │  ├─ middleware/
│  │  │  └─ main.py
│  │  ├─ tests/
│  │  │  ├─ unit/
│  │  │  ├─ integration/
│  │  │  └─ contract/
│  │  ├─ pyproject.toml
│  │  └─ uv.lock
│  ├─ worker/
│  │  ├─ app/
│  │  │  ├─ jobs/
│  │  │  │  ├─ process_ocr_job.py
│  │  │  │  └─ refresh_analytics_job.py
│  │  │  ├─ consumers/
│  │  │  ├─ services/
│  │  │  ├─ providers/
│  │  │  ├─ core/
│  │  │  └─ main.py
│  │  ├─ tests/
│  │  ├─ pyproject.toml
│  │  └─ uv.lock
│  ├─ shared/
│  │  ├─ domain/
│  │  ├─ schemas/
│  │  ├─ constants/
│  │  ├─ utils/
│  │  └─ prompts/
│  └─ docs/
│     ├─ adr/
│     ├─ api/
│     ├─ prompts/
│     └─ runbooks/
├─ infra/
│  ├─ docker/
│  │  ├─ frontend.Dockerfile
│  │  ├─ api.Dockerfile
│  │  ├─ worker.Dockerfile
│  │  └─ nginx.conf
│  ├─ compose/
│  │  ├─ docker-compose.local.yml
│  │  └─ docker-compose.staging.yml
│  ├─ db/
│  │  ├─ migrations/
│  │  └─ seed/
│  ├─ scripts/
│  ├─ monitoring/
│  └─ terraform/
├─ tasks/
│  ├─ phase-0-foundation.md
│  ├─ phase-1-auth.md
│  ├─ phase-2-receipts-ocr.md
│  ├─ phase-3-transactions.md
│  ├─ phase-4-dashboard-analytics.md
│  ├─ phase-5-budgets.md
│  ├─ phase-6-ai-chatbot.md
│  ├─ phase-7-rag-extension.md
│  ├─ phase-8-ui-redesign.md
│  ├─ phase-9-hardening-uat-release.md
│  └─ phase-10-post-mvp.md
├─ system_prompt.md
├─ project_map.md
├─ tech_stack.md
├─ roadmap.md
└─ progress_log.md
```

## Phân tách trách nhiệm lớn

### `frontend/`
Chứa toàn bộ mã giao diện và orchestration ở phía client/server-rendered UI.
- Quản lý auth flow, dashboard UI, receipt upload UI, review OCR draft, transactions CRUD, budgets, chatbot hỏi đáp chi tiêu.
- Tập trung vào trải nghiệm người dùng, loading state, error state, form state, route protection.
- Không đặt business rule phức tạp hoặc logic OCR/AI ở đây.

### `backend/`
Chứa toàn bộ năng lực xử lý nghiệp vụ, dữ liệu, background jobs và tích hợp ngoài.
- `api/`: FastAPI app, expose REST endpoints, auth/session, validation, service orchestration.
- `worker/`: xử lý nền cho OCR, analytics refresh.
- `shared/`: shared schema, prompt, domain helper để api và worker dùng chung.

## Chức năng chính theo khu vực

### Frontend Web App

#### `frontend/web/app`
Entry point theo Next.js App Router.
- Route group cho auth, dashboard, receipts, transactions, budgets, chat, settings.
- Chứa layout, page, loading, error, server component/page composition.

#### `frontend/web/components`
UI components tái sử dụng.
- `ui/`: button, input, modal, table, badge, skeleton.
- `forms/`: form field, receipt upload form, transaction form, budget form.
- `charts/`: wrappers cho chart chi tiêu, budget progress, trend chart.
- `layout/`: navbar, sidebar, header, page shell.
- `domain/`: receipt card, transaction row, chat bubble, suggested question.

#### `frontend/web/features`
Tách theo nghiệp vụ.
- `auth/`: login/register/session hooks.
- `receipts/`: upload, preview, OCR review flow.
- `transactions/`: list/filter/create/edit/delete transaction.
- `dashboard/`: summary cards, spending trends, category breakdown.
- `budgets/`: create/update budget, progress, alerts.
- `chat/`: chat UI conversational, streaming message display, history view, suggested questions.

#### `frontend/web/lib`
Hạ tầng phía frontend.
- `api/`: API client gọi backend.
- `hooks/`: reusable hooks.
- `utils/`: formatter, parser, date helpers.
- `config/`: env parsing, route constants.
- `query/`: TanStack Query setup nếu dùng.

#### `frontend/web/providers`
Global providers.
- Session provider.
- Query provider.
- Theme/config provider.

### Backend API

#### `backend/api/app/api/v1`
REST endpoints public/internal cho web app.
- `auth.py`: đăng ký, đăng nhập, refresh session, logout, me.
- `receipts.py`: upload file, lấy trạng thái, lấy OCR draft.
- `transactions.py`: CRUD transaction, filter, pagination.
- `dashboard.py`: summary, breakdown, trend.
- `budgets.py`: CRUD budget, progress, status.
- `chat.py`: chat API với SSE streaming (POST /chat/message), history CRUD.

#### `backend/api/app/core`
Hạ tầng hệ thống.
- `config.py`: settings từ env.
- `security.py`: JWT, password hashing, cookie policy.
- `database.py`: SQLModel/SQLAlchemy engine, session.
- `cache.py`: Redis client.
- `logging.py`: logger config và correlation id.

#### `backend/api/app/models`
ORM models cho PostgreSQL.
- User, ReceiptUpload, OcrResult, Transaction, Category, Budget, ChatMessage, UserMerchantMapping.

#### `backend/api/app/schemas`
Pydantic schemas vào/ra.
- Request/response DTO.
- OCR normalized payload.
- Chat message schema (role/content/tool_calls).

#### `backend/api/app/services`
Application service layer.
- Auth service.
- Receipt upload service.
- OCR draft orchestration.
- Transaction service.
- Dashboard aggregation service.
- Budget service.
- Chat orchestrator (LLM client + tool dispatch).

#### `backend/api/app/repositories`
Data access layer.
- Tách truy vấn DB ra khỏi service.
- Giữ query logic phức tạp, aggregation query, transactional writes.

#### `backend/api/app/domain`
Pure business rules.
- Validation quy tắc budget.
- Transaction categorization helper.
- Dashboard aggregation logic thuần.
- Chat tool registry và safety rules.

#### `backend/api/app/integrations`
Tích hợp ngoài qua adapter.
- `storage/`: MinIO/S3 adapter.
- `ocr/`: OCRProvider interface + PaddleOCR/EasyOCR/Google Vision adapters.
- `llm/`: Ollama/Gemini adapters.

### Backend Worker

#### `backend/worker/app/jobs`
Background job definitions.
- `process_ocr_job.py`: trích xuất dữ liệu từ receipt image.
- `refresh_analytics_job.py`: recompute summary/cache khi transaction thay đổi.

#### `backend/worker/app/consumers`
Queue handlers, retry policy, dead-letter strategy.

#### `backend/worker/app/services`
Logic xử lý nền tách khỏi queue framework.

#### `backend/worker/app/providers`
Provider wiring cho OCR, storage, LLM, notification.

### Shared Backend

#### `backend/shared/domain`
Logic nghiệp vụ dùng chung giữa api và worker.

#### `backend/shared/schemas`
Schema chuẩn hóa dùng lại để tránh lệch contract.

#### `backend/shared/prompts`
Prompt versioning cho normalize OCR và system prompt chatbot.

## Mapping module với functional requirements

### Auth
- `frontend/web/features/auth`
- `backend/api/app/api/v1/auth.py`
- `backend/api/app/services/auth_service.py`

### Receipts & OCR
- `frontend/web/features/receipts`
- `backend/api/app/api/v1/receipts.py`
- `backend/api/app/integrations/ocr/`
- `backend/worker/app/jobs/process_ocr_job.py`

### Transactions
- `frontend/web/features/transactions`
- `backend/api/app/api/v1/transactions.py`
- `backend/api/app/services/transaction_service.py`
- `backend/shared/domain/transactions.py`

### Dashboard & Analytics
- `frontend/web/features/dashboard`
- `backend/api/app/api/v1/dashboard.py`
- `backend/api/app/services/dashboard_service.py`
- `backend/worker/app/jobs/refresh_analytics_job.py`

### Budgets
- `frontend/web/features/budgets`
- `backend/api/app/api/v1/budgets.py`
- `backend/api/app/services/budget_service.py`

### AI Chatbot
- `frontend/web/app/chat/` (chat UI, streaming, history, suggested questions)
- `backend/api/app/api/v1/chat.py` (SSE endpoint + history CRUD)
- `backend/api/app/services/chat/` (query layer, llm client, orchestrator, safety)
- `backend/shared/prompts/` (system prompt tiếng Việt cho chatbot)

## Luồng dữ liệu end-to-end
1. User upload receipt ở frontend.
2. Backend API lưu metadata + object storage path.
3. Backend API enqueue `process_ocr_job`.
4. Worker gọi OCR provider và chuẩn hóa kết quả thành draft.
5. Frontend lấy draft để user review/chỉnh sửa.
6. User lưu transaction.
7. Backend ghi transaction + enqueue `refresh_analytics_job`.
8. Dashboard summary được recompute/cache trong Redis hoặc DB snapshot.
9. Backend API enqueue hoặc gọi analytics refresh job khi cần precompute.
10. Frontend hiển thị dashboard + user có thể mở trang /chat để hỏi đáp tự nhiên.
11. Chatbot nhận câu hỏi, gọi các query tool trên backend (scoped theo user_id), tổng hợp → trả lời streaming.

## Boundary quan trọng
- Frontend không được gọi OCR/LLM trực tiếp.
- Backend API không giữ xử lý OCR/AI nặng trong request lifecycle nếu có thể đẩy sang worker.
- Worker không quyết định UI state; chỉ cập nhật processing state và output chuẩn hóa.
- AI insight chỉ đọc summary data hoặc structured transaction data, không đọc raw image trực tiếp.
- Chatbot truy cập DB qua tool layer backend scoped theo user_id; LLM không nhận raw SQL, không bao giờ có DB credentials.
- Business rules nằm ở backend domain/service layer, không nằm trong component UI.

## Thứ tự ưu tiên khi triển khai
1. Foundation + infra local.
2. Backend auth + frontend auth flow.
3. Receipt upload + OCR draft.
4. Transaction CRUD.
5. Dashboard summary.
6. Budget.
7. AI chatbot.
8. Hardening, observability, UAT.
