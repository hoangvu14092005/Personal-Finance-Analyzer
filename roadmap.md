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
| 6 | AI Insights | Insight generation pipeline, cache, UI, safety fallback |
| 7 | Hardening, UAT & Release | Observability, security, performance, test pack, release checklist |
| 8 | Post-MVP | Export, insight history, OCR optimization, personalization |

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

## Phase 6 - AI Insights
### Mục tiêu
Sinh insight bám dữ liệu thật, có schema ổn định, có cache và fallback an toàn.

### Deliverables
- Summary-to-LLM input builder
- Insight provider adapter cho Ollama/Gemini
- TaskIQ job `generate_insight_job`
- Pydantic output schema + post-validation checks
- Insight APIs + insight UI
- Caching theo data fingerprint

### Done khi
- Hệ thống sinh ra insights/recommendations/alerts parse được
- Insight không mâu thuẫn rõ ràng với summary data
- Thiếu dữ liệu thì trả fallback có kiểm soát

## Phase 7 - Hardening, UAT & Release
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

## Phase 8 - Post-MVP
### Mục tiêu
Mở rộng sản phẩm sau khi MVP ổn định và có usage thực tế.

### Candidate scope
- OCR optimization theo vendor/template
- Export CSV/PDF
- Insight history
- Merchant learning nâng cao
- Personalization sâu hơn
- Explainability tốt hơn cho insight

## Thứ tự triển khai khuyến nghị
1. Foundation
2. Auth
3. Receipt upload + OCR mock pipeline
4. Draft review + transaction save
5. Dashboard summary
6. Budget integration
7. AI insight với provider mock trước, provider thật sau
8. Hardening + UAT + release

## Cách dùng roadmap trong vibecoding
1. Đọc `progress_log.md` trước khi viết code.
2. Xác định phase hiện tại và chỉ chọn 1-3 task nhỏ để làm.
3. Sau mỗi task, chạy lint/test tối thiểu trong phạm vi bị ảnh hưởng.
4. Khi xong một phần, ghi lại decision + file changed + trạng thái vào `progress_log.md`.
5. Chỉ mở phase tiếp theo khi exit criteria phase hiện tại đã đạt.
