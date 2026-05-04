# Kiến trúc Backend — Personal Finance Analyzer

> Tài liệu phân tích kiến trúc, cấu trúc thư mục, từng file và từng hàm của toàn bộ backend (`backend/api`, `backend/worker`, `backend/shared`).
>
> **Phiên bản code phân tích:** mốc M5 (xem comment trong `pfa_shared/entities.py`, `app/services/ocr_queue.py`).

## Mục lục các tài liệu

Để dễ đọc, phân tích được tách thành các file con trong cùng thư mục:

1. [`01-overview.md`](./01-overview.md) — Tổng quan + Sơ đồ kiến trúc + Sơ đồ luồng dữ liệu + ERD
2. [`02-structure.md`](./02-structure.md) — Cây thư mục `backend/` chi tiết
3. [`03-shared.md`](./03-shared.md) — Phân tích `backend/shared` (`pfa_shared`)
4. [`04-api-core.md`](./04-api-core.md) — Phân tích `backend/api/app/{main,core,middleware,dependencies}`
5. [`05-api-routers.md`](./05-api-routers.md) — Phân tích `backend/api/app/api/*` (routers)
6. [`06-api-services.md`](./06-api-services.md) — Phân tích `backend/api/app/services/*`
7. [`07-api-integrations.md`](./07-api-integrations.md) — Phân tích `backend/api/app/{integrations,schemas,models}`
8. [`08-worker.md`](./08-worker.md) — Phân tích `backend/worker`
9. [`09-migrations.md`](./09-migrations.md) — Alembic migrations + Dependency matrix + Patterns
