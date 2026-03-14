# Phase 0 - Foundation & Architecture

## Outcome
Có nền tảng repo chạy local được với `frontend`, `backend/api`, `backend/worker`, local infra đầy đủ và khung dữ liệu lõi.

## Task breakdown

### 0.1 Tạo cấu trúc repo chuẩn
- Tạo root structure:
  - `frontend/web`
  - `backend/api`
  - `backend/worker`
  - `backend/shared`
  - `infra/docker`
  - `docs`
- Tạo README root mô tả cách chạy local.
- Acceptance:
  - Repo phản ánh đúng boundary frontend/backend/worker.

### 0.2 Khởi tạo frontend Next.js
- Tạo app Next.js 15 App Router với TypeScript.
- Cài Tailwind CSS.
- Tạo layout shell, trang landing, trang health check UI đơn giản.
- Chọn `pnpm` cho frontend package manager.
- Acceptance:
  - Frontend chạy local và render được trang mặc định.

### 0.3 Khởi tạo backend API FastAPI
- Tạo app FastAPI với cấu trúc:
  - `app/main.py`
  - `app/api/`
  - `app/core/`
  - `app/models/`
  - `app/schemas/`
  - `app/services/`
  - `app/repos/`
- Dùng `uv` để quản lý dependencies Python.
- Tạo endpoint `GET /health`.
- Acceptance:
  - API chạy local và trả health 200.

### 0.4 Khởi tạo worker TaskIQ
- Tạo worker app riêng dùng `uv`.
- Cấu hình TaskIQ + Redis broker.
- Tạo 1 demo task `ping_task`.
- Acceptance:
  - Worker connect được Redis và consume demo task.

### 0.5 Cấu hình shared Python package
- Tạo `backend/shared` cho:
  - config,
  - logging,
  - enums,
  - common schemas,
  - utility helpers.
- Export được cho cả api và worker dùng chung.
- Acceptance:
  - API và worker import được shared package.

### 0.6 Thiết lập local infra
- Tạo `docker-compose.yml` cho:
  - PostgreSQL 16
  - Redis 7
  - MinIO
- Tạo script khởi tạo bucket local.
- Tạo `.env.example` cho frontend, api, worker.
- Acceptance:
  - Toàn bộ services local up thành công.

### 0.7 Database schema v1
- Chọn Alembic cho migrations.
- Tạo SQLModel models cho:
  - User
  - ReceiptUpload
  - OcrResult
  - Transaction
  - Category
  - Budget
  - InsightSnapshot
  - UserMerchantMapping
- Tạo migration đầu tiên.
- Seed category mặc định.
- Acceptance:
  - `alembic upgrade head` chạy thành công.

### 0.8 Config, logging, settings
- Tạo settings bằng Pydantic Settings.
- Tạo logger dùng chung.
- Thêm request id/correlation id cơ bản.
- Chuẩn hóa environment names: local, test, staging, prod.
- Acceptance:
  - API log được request lifecycle cơ bản.

### 0.9 Code quality baseline
- Python:
  - Ruff
  - mypy
  - pytest
- Frontend:
  - ESLint mặc định Next.js
  - TypeScript strict mode
- Tạo scripts root hoặc docs command cho lint/test/typecheck.
- Acceptance:
  - Các lệnh check cơ bản chạy pass trên skeleton.

### 0.10 Frontend gọi backend health
- Thêm config base URL cho frontend.
- Tạo route hoặc page gọi `GET /health`.
- Hiển thị trạng thái API online/offline.
- Acceptance:
  - Kiểm chứng được kết nối frontend -> backend.

### 0.11 CI baseline
- Tạo pipeline chạy:
  - frontend lint + typecheck
  - backend ruff + mypy + pytest
- Acceptance:
  - CI pass với skeleton repo.

## Exit criteria phase 0
- Frontend, API, worker, DB, Redis, MinIO chạy được local.
- Có schema dữ liệu lõi và migration đầu tiên.
- Có baseline chất lượng code và CI.

