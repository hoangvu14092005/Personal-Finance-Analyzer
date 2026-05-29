# roadmap.md

## Mục tiêu
Hoàn thành MVP của **Personal Finance Analyzer (Web)** với kiến trúc tách riêng **frontend** và **backend**, dùng **Next.js + FastAPI + PostgreSQL + Redis + TaskIQ**, hỗ trợ auth, upload receipt, OCR bất đồng bộ, transaction management, dashboard analytics, budgets và AI insights.

## Kiến trúc triển khai tổng thể
- **Frontend**: Next.js App Router, TypeScript, Tailwind CSS, TanStack Query.
- **Backend API**: FastAPI, Pydantic 2, SQLModel, PyJWT qua HttpOnly Cookies.
- **Worker**: TaskIQ + Redis để xử lý OCR, precompute analytics và AI insight jobs.
- **Data layer**: PostgreSQL 16, MinIO local hoặc S3 production.
- **AI/OCR adapters**: thiết kế theo provider pattern để thay provider mà không phá business logic.

## Nguyên tắc thực hiện
- Đi theo phase nhỏ, mỗi phase có output rõ ràng và chạy được.
- Luôn ưu tiên **end-to-end vertical slice** trước khi tối ưu sâu.
- Tách rõ trách nhiệm giữa frontend, backend API và worker.
- Mọi API input/output phải có schema Pydantic typed rõ ràng.
- Mọi thay đổi hoàn tất phải cập nhật `progress_log.md`.
- Mỗi phase chỉ mở khi exit criteria của phase trước đã pass.

## Phase overview

| Phase | Mục tiêu | Kết quả chính |
|---|---|---|
| 0 | Foundation & Architecture | Monorepo, infra local, app skeleton, DB schema, queue, CI |
| 1 | Auth & Session | Register/login/logout, protected routes, onboarding profile |
| 2 | Receipt Upload & OCR Pipeline | Upload file, storage, enqueue OCR, draft extraction |
| 3 | Transactions & Review | Review OCR draft, manual entry, CRUD transaction |
| 4 | Dashboard & Analytics | Summary, filters, charts, compare previous period |
| 5 | Budgets | Budget CRUD, usage calculation, warnings |
| 6 | AI Chatbot | Chat conversational với function calling, query on-demand từ DB thực, không hallucinate |
| 7 | RAG Extension | pgvector + embedding, 2 RAG tools (search_receipt_text, semantic_search_transactions) |
| 8 | UI Redesign | Apply DESIGN.md: white canvas + yellow CTA + IBM Plex Sans + cards hairline |
| 9 | Hardening, UAT & Release | Observability, security, performance, test pack, release checklist |
| 10 | Post-MVP | Export, insight history, OCR optimization, personalization |

## Phase 0 - Foundation & Architecture
### Mục tiêu
Dựng nền tảng repo và runtime để frontend, backend và worker cùng chạy local ổn định.

### Deliverables
- Repo structure tách rõ `frontend/` và `backend/`
- Frontend Next.js skeleton + backend FastAPI skeleton + worker TaskIQ skeleton
- `uv` cho Python apps và `pnpm` cho frontend workspace
- Docker Compose cho Postgres, Redis, MinIO
- SQLModel models + Alembic migration đầu tiên
- Config, logger, env example, health checks
- CI baseline cho lint, typecheck, unit test

### Done khi
- `frontend`, `backend/api`, `backend/worker` chạy local cùng lúc
- API kết nối được Postgres, Redis, MinIO
- Frontend gọi được health endpoint từ backend
- Typecheck, lint, test pass ở mức skeleton

## Phase 1 - Auth & Session
### Mục tiêu
Xây dựng auth flow đầy đủ với session bảo mật và onboarding profile cơ bản.

### Deliverables
- Register/login/logout APIs bằng FastAPI
- Password hashing + JWT access/session flow qua HttpOnly Cookies
- Auth middleware/dependencies cho backend
- Login/register pages + protected routes trên frontend
- User profile mặc định: currency, timezone, locale cơ bản

### Done khi
- User đăng ký, đăng nhập, đăng xuất được
- Protected pages chặn được user chưa auth
- Cookie/session hoạt động ổn định qua refresh trình duyệt

## Phase 2 - Receipt Upload & OCR Pipeline
### Mục tiêu
Cho phép user upload receipt, lưu file vào storage, gửi OCR job sang worker và nhận draft extraction.

### Deliverables
- Upload endpoint + validation file
- MinIO/S3 abstraction
- TaskIQ job `process_ocr_job`
- `OCRProvider` adapter + mock provider + local OCR provider baseline
- Receipt status polling endpoint
- OCR normalized result model

### Done khi
- Upload thành công sinh ra receipt record + object storage path
- Worker consume OCR job thành công
- Receipt có trạng thái `uploaded -> processing -> ready/failed`
- Draft extraction hiển thị được cho frontend

## Phase 3 - Transactions & Review
### Mục tiêu
Biến OCR draft thành transaction chính thức và hỗ trợ nhập tay, sửa, xóa, lọc.

### Deliverables
- Draft review form trên frontend
- Transaction CRUD APIs trên backend
- Category suggestion baseline
- Manual entry flow
- Trigger analytics refresh sau mutation

### Done khi
- User hoàn tất luồng upload -> OCR -> review -> save transaction
- User tạo transaction thủ công được
- Dashboard data được refresh sau create/update/delete

## Phase 4 - Dashboard & Analytics
### Mục tiêu
Hiển thị dashboard phản ánh đúng dữ liệu chi tiêu theo range filter.

### Deliverables
- Aggregation service cho summary cards, top categories, recent transactions
- Dashboard summary API
- Time filter UX trên frontend
- Previous-period comparison logic
- Chart rendering và loading states
- Cache/precompute baseline nếu cần

### Done khi
- Dashboard hiển thị đúng theo filter
- Không full reload khi đổi filter
- Dữ liệu summary khớp transaction data trong DB

## Phase 5 - Budgets
### Mục tiêu
Cho phép user đặt ngân sách theo category và nhìn thấy mức sử dụng, cảnh báo vượt ngưỡng.

### Deliverables
- Budget SQLModel + CRUD APIs
- Budget usage calculation service
- Dashboard integration cho used vs budget
- Budget management UI

### Done khi
- User tạo/sửa/xóa budget được
- Dashboard hiển thị đúng % used và exceeded state
- Warning khớp dữ liệu giao dịch thực tế

## Phase 6 - AI Chatbot
### Mục tiêu
Xây dựng chatbot conversational cho phép user hỏi đáp tự nhiên về chi tiêu cá nhân.
Tất cả số liệu phải từ DB thực (không hallucinate), tái sử dụng services sẵn có.

### Deliverables
- Bỏ module insight cũ (one-shot, fix cứng, UX kém linh hoạt)
- Chat query service layer: wrap các analytics/budget services thành tools LLM gọi được
- LLM client OpenAI-compatible với function calling + streaming (SSE)
- Chat orchestrator: multi-turn loop, tool execution, history management
- Chat API endpoints: POST message (SSE), GET history, DELETE history
- Table `chat_messages` persist unlimited lịch sử theo user
- Frontend chat UI thay trang /insights cũ, match design tokens hiện tại
- Safety layer: banned phrases, rate limit, user isolation enforcement

### Provider
- Endpoint mặc định: `http://localhost:20128/v1` (OpenAI-compatible)
- Model: `cx/gpt-5.5`
- Đã verify: function calling + streaming + multi-turn tool result hoạt động

### Done khi
- User hỏi "Tháng này tôi tiêu bao nhiêu ở Grab?" → bot trả lời số chính xác từ DB
- ≥ 5 loại câu hỏi phổ biến hoạt động: tổng chi, so sánh kỳ, top merchant, budget, search
- Streaming mượt, first token < 300ms
- Chat history persist và load lại được khi reload page
- Không leak data giữa users (tool execute với đúng user_id server-side)
- Backend coverage > 80% cho module `services/chat/`

## Phase 7 - RAG Extension
### Mục tiêu
Mở rộng chatbot sang hybrid retrieval: SQL tools (số liệu) + RAG tools (nội dung text).

### Deliverables
- pgvector extension + ReceiptTextChunk entity + Transaction.search_embedding column
- Local embedding client (sentence-transformers, multilingual MiniLM, 384-dim)
- Index pipeline worker: embed OCR text khi receipt ready
- Tool search_receipt_text: tìm nội dung chi tiết hóa đơn
- Tool semantic_search_transactions: search theo ý nghĩa mơ hồ
- System prompt update với RAG usage rules

### Deferred hardening
- Unit tests cho RAG retrieval với mock embedding client.
- Sửa receipt RAG filter để tìm được receipt chưa confirm theo `receipt_uploads.merchant_name`, `receipt_date`, `created_at`.
- Trả structured evidence gồm chunk_id, score/distance, receipt metadata, invoice/transaction links.
- Bổ sung hybrid keyword + vector search và rerank nếu retrieval chất lượng chưa đủ.
- Thêm deterministic date parser tiếng Việt cho “hôm qua”, “tuần trước”, “ngày 18/5”.
- Apply `category_name` filter thật cho `semantic_search_transactions`.

### Done khi
- User hỏi "Hóa đơn Grab ngày X có món gì?" → bot trả đúng từ OCR
- User hỏi "Tôi có mua đồ skincare không?" → semantic match được
- Không leak data giữa users
- SQL vẫn là source of truth cho số liệu

## Phase 8 - UI Redesign
### Mục tiêu
Apply design system mô tả trong DESIGN.md (PostHog-style) cho toàn bộ frontend.

### Deliverables
- Tailwind theme extend với design tokens (colors, typography, spacing, radius)
- IBM Plex Sans Variable font loading
- Primitive components: Button, Card, Input, PillTab, CalloutBanner, Badge
- Layout chrome: Nav + Footer + MobileDrawer
- Redesign mỗi page: landing, auth, dashboard, transactions, receipts, budgets, chat
- Responsive mobile/tablet/desktop
- Accessibility Lighthouse ≥ 90

### Done khi
- Canvas white #ffffff, yellow CTA #f7a501, IBM Plex Sans ở mọi page
- Cards flat với hairline borders, không drop-shadow
- Chat UI có mascot + bubbles phân biệt user/assistant đúng spec
- E2E Playwright tests pass sau migration
- Lighthouse accessibility ≥ 90

## Phase 9 - Hardening, UAT & Release
### Mục tiêu
Đưa MVP lên mức đủ ổn định để UAT và release.

### Deliverables
- Logging, metrics, tracing/correlation id cơ bản
- Retry/timeout/idempotency cho upload, OCR, AI jobs
- Security review checklist
- Performance tuning cho dashboard, queue, DB queries
- UAT checklist + regression suite cơ bản
- Release runbook + rollback notes

### Done khi
- Pass UAT các luồng chính
- Không còn blocker/critical bug
- Có đủ tài liệu để deploy staging/prod

## Phase 10 - Post-MVP
### Mục tiêu
Mở rộng sản phẩm sau khi MVP ổn định và có usage thực tế.

### Candidate scope
- OCR optimization theo vendor/template
- Export CSV/PDF
- Chat memory RAG (summarize history qua N messages)
- App knowledge RAG (FAQ, user guide)
- Merchant learning nâng cao
- Personalization sâu hơn
- Explainability cho chat answer (hiển thị transactions được tính vào tổng)
- Reranking với cross-encoder + hybrid search BM25+vector
- Custom mascot illustrations thay emoji placeholder

## Thứ tự triển khai khuyến nghị
1. Foundation
2. Auth
3. Receipt upload + OCR mock pipeline
4. Draft review + transaction save
5. Dashboard summary
6. Budget integration
7. AI chatbot với function calling (provider OpenAI-compatible, `cx/gpt-5.5`)
8. RAG extension (receipt OCR search + semantic transaction search)
9. UI redesign theo DESIGN.md
10. Hardening + UAT + release
11. Post-MVP (optional phases)

## Cách dùng roadmap trong vibecoding
1. Đọc `progress_log.md` trước khi viết code.
2. Xác định phase hiện tại và chỉ chọn 1-3 task nhỏ để làm.
3. Sau mỗi task, chạy lint/test tối thiểu trong phạm vi bị ảnh hưởng.
4. Khi xong một phần, ghi lại decision + file changed + trạng thái vào `progress_log.md`.
5. Chỉ mở phase tiếp theo khi exit criteria phase hiện tại đã đạt.
