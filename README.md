# Personal Finance Analyzer

Monorepo ứng dụng quản lý chi tiêu cá nhân với AI: upload hóa đơn → OCR tự động → dashboard phân tích → chatbot hỏi đáp bằng tiếng Việt.

## Tech Stack

- **Frontend**: Next.js 15 + React 19 + Tailwind CSS v4 + Recharts
- **Backend API**: FastAPI + SQLModel + JWT (HttpOnly cookie)
- **Worker**: TaskIQ + Redis cho OCR + RAG indexing
- **Data**: PostgreSQL 16 + pgvector, MinIO (S3-compatible)
- **AI**:
  - LLM: OpenAI-compatible endpoint (`cx/gpt-5.5`) — chat + vision OCR
  - Embeddings: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (local, 384-dim)

## Features

- ✅ Auth (register/login/logout/me)
- ✅ Upload hóa đơn → **LLM Vision OCR** (real, không phải mock)
- ✅ Review form với low-confidence highlight + category suggestion
- ✅ Transactions CRUD + filter/pagination
- ✅ Dashboard analytics (date presets, donut chart, previous-period compare)
- ✅ Budgets per category per month + usage tracking
- ✅ **AI Chatbot** với function calling (SQL tools + RAG tools)
- ✅ **RAG search** trên OCR content + semantic transaction search (pgvector)
- ✅ UI redesign theo design system (cream canvas, yellow CTA, IBM Plex Sans)

## Repository Structure

```
frontend/web/          # Next.js app (pages, components/ui, components/layout, lib)
backend/
  api/                 # FastAPI (core, api/v1, services, services/chat, dependencies)
  worker/              # TaskIQ worker (tasks, index_tasks, ocr_provider)
  shared/pfa_shared/   # SQLModel entities, config, storage adapters
infra/docker/          # PostgreSQL + Redis + MinIO docker-compose
docs/                  # Architecture documentation
.kiro/specs/           # Feature specs (requirements / design / tasks)
tasks/                 # Phase task breakdowns
```

---

## Prerequisites

- **Docker Desktop** (chạy infrastructure)
- **Python 3.12+**
- **Node.js 20+** và **pnpm** (qua corepack)
- **LLM endpoint** chạy tại `http://localhost:20128/v1` (OpenAI-compatible, hỗ trợ vision + function calling)

---

## First-time Setup (1 lần)

### 1. Start infrastructure

```powershell
Set-Location "infra\docker"
docker compose up -d
```

Verify 3 services healthy:
```powershell
docker ps --filter "name=pfa-"
```

Expected:
- `pfa-postgres-dev` — PostgreSQL + pgvector trên port **5433**
- `pfa-redis-dev` — Redis trên port 6379
- `pfa-minio-dev` — MinIO API trên port 9000, Console trên 9001

> **Note**: PostgreSQL dùng port **5433** (không phải 5432) để tránh conflict với PostgreSQL native trên Windows.

### 2. Install backend dependencies

```powershell
Set-Location "backend\api"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ..\shared
.\.venv\Scripts\python.exe -m pip install -e .
```

Worker dùng chung `.venv` với API (tránh download lại model sentence-transformers ~500MB).

### 3. Apply database migration + seed categories

```powershell
Set-Location "backend\api"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.seed_categories
```

Migration sẽ:
- Tạo tất cả tables (users, transactions, receipts, budgets, chat_messages, receipt_text_chunks, ...)
- Enable pgvector extension
- Tạo IVFFlat indexes cho vector search

### 4. Setup environment files

Copy `.env.example` → `.env` trong cả 3 folder và điền LLM config:

```powershell
Copy-Item backend\api\.env.example backend\api\.env
Copy-Item backend\worker\.env.example backend\worker\.env
```

Chỉnh trong `backend/api/.env` và `backend/worker/.env`:
```
CHAT_LLM_BASE_URL=http://localhost:20128/v1
CHAT_LLM_API_KEY=sk-your-api-key-here
CHAT_LLM_MODEL=cx/gpt-5.5
STORAGE_BACKEND=s3
DATABASE_URL=postgresql+psycopg://pfa:pfa@localhost:5433/pfa
```

Worker cần thêm:
```
OCR_PROVIDER=llm_vision
```

### 5. Install frontend

```powershell
Set-Location "frontend\web"
corepack pnpm install
```

---

## Chạy hàng ngày (4 terminals)

### Terminal 1 — Docker services

```powershell
Set-Location "infra\docker"
docker compose up -d
```

### Terminal 2 — Backend API

```powershell
Set-Location "backend\api"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API ready tại `http://127.0.0.1:8000` · Swagger UI tại `/docs`

### Terminal 3 — Worker (OCR + RAG indexing)

```powershell
Set-Location "backend\worker"
..\api\.venv\Scripts\python.exe -m taskiq worker --app-dir . worker_app:broker tasks index_tasks
```

Worker sẽ import cả `tasks` (process_ocr_job) và `index_tasks` (index_receipt_text).

### Terminal 4 — Frontend

```powershell
Set-Location "frontend\web"
corepack pnpm dev
```

Frontend ready tại `http://localhost:3000`

---

## URLs

| URL | Dùng cho |
|---|---|
| http://localhost:3000 | Landing page |
| http://localhost:3000/register | Đăng ký |
| http://localhost:3000/login | Đăng nhập |
| http://localhost:3000/dashboard | Dashboard (protected) |
| http://localhost:3000/receipts/upload | Upload hóa đơn |
| http://localhost:3000/transactions | Lịch sử giao dịch |
| http://localhost:3000/transactions/new | Nhập tay |
| http://localhost:3000/budgets | Quản lý ngân sách |
| http://localhost:3000/chat | 💬 Trợ lý AI |
| http://127.0.0.1:8000/docs | API Swagger UI |
| http://localhost:9001 | MinIO Console (minioadmin / minioadmin) |

---

## Smoke Test Flow

1. Mở `http://localhost:3000` → bấm "Bắt đầu miễn phí"
2. Đăng ký tài khoản → login
3. Vào `/receipts/upload` → upload ảnh hóa đơn (JPG/PNG, < 10MB)
4. Đợi ~10-20s cho LLM Vision OCR chạy
5. Tự động redirect sang review form → lưu transaction
6. Vào `/chat` → hỏi một số câu:
   - "Tháng này tôi tiêu bao nhiêu?" (SQL tool)
   - "Hóa đơn Grab tuần này có món gì?" (RAG tool — receipt content)
   - "Tôi có mua đồ skincare không?" (semantic search)

---

## Scripts

### Backend quality checks

```powershell
Set-Location "backend\api"
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m pytest
```

### Worker quality checks

```powershell
Set-Location "backend\worker"
..\api\.venv\Scripts\python.exe -m ruff check .
..\api\.venv\Scripts\python.exe -m mypy .
..\api\.venv\Scripts\python.exe -m pytest
```

### Frontend quality checks

```powershell
Set-Location "frontend\web"
corepack pnpm lint
corepack pnpm build
npx tsc --noEmit
corepack pnpm e2e  # Playwright — cần backend + infra up
```

### Backfill embeddings (nếu đã có data cũ trước Phase 7)

```powershell
Set-Location "backend\api"
.\.venv\Scripts\python.exe -m scripts.backfill_receipt_embeddings
.\.venv\Scripts\python.exe -m scripts.backfill_transaction_embeddings
```

---

## Environment Variables

### `backend/api/.env`

| Variable | Default | Mô tả |
|---|---|---|
| `APP_ENV` | `local` | local / test / staging / prod |
| `DATABASE_URL` | `postgresql+psycopg://pfa:pfa@localhost:5433/pfa` | PostgreSQL URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL |
| `STORAGE_BACKEND` | `local` | `local` hoặc `s3` (MinIO) |
| `S3_ENDPOINT` | `http://localhost:9000` | MinIO endpoint |
| `JWT_SECRET` | dev placeholder | **Bắt buộc override** ở staging/prod |
| `CHAT_LLM_BASE_URL` | `http://localhost:20128/v1` | OpenAI-compatible endpoint |
| `CHAT_LLM_API_KEY` | — | API key |
| `CHAT_LLM_MODEL` | `cx/gpt-5.5` | Model name |

### `backend/worker/.env`

Tương tự API + thêm:

| Variable | Default | Mô tả |
|---|---|---|
| `OCR_PROVIDER` | `mock` | `mock` hoặc `llm_vision` |

### `frontend/web/.env.local` (optional)

```
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

---

## Troubleshooting

| Vấn đề | Fix |
|---|---|
| `password authentication failed for user pfa` khi chạy alembic | Port 5432 đang bị PostgreSQL native Windows chiếm. Docker đã map sang 5433. Check `DATABASE_URL` trong `.env` có `localhost:5433` |
| Worker không xử lý OCR | Check `backend/worker/.env` có `OCR_PROVIDER=llm_vision` + `CHAT_LLM_*` đầy đủ |
| `storage_key missing` khi OCR | Cả API và Worker phải set `STORAGE_BACKEND=s3` để dùng chung MinIO |
| Chat trả "Unknown tool" | Reinstall shared package editable: `pip install -e ..\shared` |
| Embedding model load chậm (~30s) lần đầu | Bình thường, model ~500MB download từ HuggingFace. Cache sau đó |
| Playwright e2e fail | Cần Docker + backend API + worker đều chạy; chạy `pnpm e2e:ui` để debug |
| Frontend không connect API | Kiểm tra `NEXT_PUBLIC_API_BASE_URL` và CORS origin trong API |

---

## Architecture Overview

```
User Browser
    │
    ├─ Frontend (Next.js) ──────┐
    │                            ▼
    │                     Backend API (FastAPI)
    │                       │       │
    │                       │       ├─ SQLModel ──► PostgreSQL (+ pgvector)
    │                       │       ├─ boto3 ─────► MinIO (S3)
    │                       │       └─ TaskIQ ────► Redis (queue)
    │                       │                         │
    │                       │                         ▼
    │                       │                    Worker
    │                       │                    ├─ LLM Vision OCR
    │                       │                    └─ sentence-transformers (embed)
    │                       │
    │                       └─ Chat Orchestrator
    │                           └─ LLM (cx/gpt-5.5)
    │                               ├─ Function calling → SQL tools
    │                               └─ RAG tools → pgvector search
```

Xem chi tiết: [`docs/`](./docs/) và [`project_map.md`](./project_map.md).

---

## Roadmap Status

- [x] **Phase 0**: Foundation (monorepo, infra, CI)
- [x] **Phase 1**: Auth & session
- [x] **Phase 2**: Receipt upload + OCR pipeline
- [x] **Phase 3**: Transactions CRUD + review form
- [x] **Phase 4**: Dashboard analytics
- [x] **Phase 5**: Budgets
- [x] **Phase 6**: AI Chatbot (function calling, SSE streaming)
- [x] **Phase 7**: RAG Extension (pgvector + LLM Vision OCR)
- [x] **Phase 8**: UI Redesign (DESIGN.md)
- [ ] **Phase 9**: Hardening, UAT & Release
- [ ] **Phase 10**: Post-MVP (export, chat memory RAG, knowledge base)

Chi tiết mỗi phase: [`tasks/phase-N-*.md`](./tasks/).

---

## License

Internal project.
