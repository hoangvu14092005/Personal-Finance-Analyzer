# Personal Finance Analyzer

Monorepo cho ung dung quan ly chi tieu ca nhan, gom frontend, backend API, worker va local infrastructure.

## Repository Structure

- `frontend/web`: Web app (Next.js)
- `backend/api`: FastAPI service
- `backend/worker`: Background worker
- `backend/shared`: Shared Python package dung chung cho API/worker
- `infra/docker`: Dockerfiles va local container setup
- `docs`: Tai lieu du an

## Local Run (Current)

Trang thai hien tai da chay duoc:
- Frontend (Next.js 15 + React 19 + Tailwind + Recharts)
- Backend API (FastAPI)
- Worker (TaskIQ + Redis)
- Local infra (PostgreSQL, Redis, MinIO)
- Auth flow (register/login/logout/me)
- Receipt upload flow + polling status + OCR mock baseline
- Receipt review form (low-confidence highlight + category suggestion)
- Manual transaction entry + Transactions history (filter/pagination/delete)
- Dashboard analytics (time presets, donut chart, previous-period compare)

### One-shot (Copy 1 Block)

Chay block sau trong PowerShell tai root repo `D:\VuLapTrinh2\Personal_Finance_Analyzer`.
Block nay se:
- up local infra (PostgreSQL, Redis, MinIO),
- mo 3 terminal rieng cho API, worker, frontend,
- in ra URL de check nhanh.

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer"

# 1) Start infra
Set-Location "infra\docker"
docker compose up -d
Set-Location "..\.."

# 2) Start API in new terminal
Start-Process powershell -ArgumentList @(
	"-NoExit",
	"-Command",
	"Set-Location 'D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\api'; python -m uv sync --all-groups; python -m uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
)

# 3) Start worker in new terminal
Start-Process powershell -ArgumentList @(
	"-NoExit",
	"-Command",
	"Set-Location 'D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker'; python -m uv sync --all-groups; python -m uv run taskiq worker --app-dir 'D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker' worker_app:broker"
)

# 4) Start frontend in new terminal
Start-Process powershell -ArgumentList @(
	"-NoExit",
	"-Command",
	"Set-Location 'D:\VuLapTrinh2\Personal_Finance_Analyzer\frontend\web'; pnpm install; pnpm dev"
)

Write-Host "Infra/API/Worker/Frontend are starting..."
Write-Host "API health: http://127.0.0.1:8000/health"
Write-Host "Frontend : http://localhost:3000"
Write-Host "API docs : http://127.0.0.1:8000/docs"
```

### 1) Prerequisites

- Node.js 20+
- pnpm
- Python 3.12+
- uv (hoac su dung `python -m uv`)
- Docker Desktop (hoac Docker daemon)

### 2) Run Backend API

PowerShell:

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\api"
python -m uv sync --all-groups
python -m uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Neu ban muon chay tu bat ky thu muc nao (an toan hon), dung lenh nay:

```powershell
python -m uv run uvicorn --app-dir "D:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api" app.main:app --reload --host 0.0.0.0 --port 8000
```

Kiem tra health:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

Expected:

```json
{"status":"ok","service":"api"}
```

### 2.1) Run Local Infra

Luu y: can mo Docker Desktop (hoac Docker daemon) truoc khi chay command.

PowerShell:

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\infra\docker"
docker compose up -d
docker compose ps
```

Services:
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

MinIO default credentials:
- username: `minioadmin`
- password: `minioadmin`

Bucket `pfa-receipts` duoc tao tu dong boi init service `minio-init`.

Kiem tra nhanh init logs:

```powershell
docker compose logs minio-init
```

Dung local infra:

```powershell
docker compose down
```

### 3) Run Frontend

Mo terminal khac, chay:

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\frontend\web"
pnpm install
pnpm dev
```

Mo trinh duyet:
- Frontend home: http://localhost:3000
- Frontend health page: http://localhost:3000/health
- Frontend login page: http://localhost:3000/login
- Frontend register page: http://localhost:3000/register
- Frontend dashboard (protected): http://localhost:3000/dashboard
- Frontend receipt upload: http://localhost:3000/receipts/upload
- Frontend transactions history: http://localhost:3000/transactions
- Frontend manual entry: http://localhost:3000/transactions/new
- Backend API docs: http://127.0.0.1:8000/docs

### 4) Run Worker

Can Redis chay tai `localhost:6379`.

PowerShell:

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker"
python -m uv sync --all-groups
python -m uv run taskiq worker --app-dir "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" worker_app:broker
```

Mo terminal khac de ban demo task:

```powershell
python -m uv run --project "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" python "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker\run_ping.py"
```

Expected output:

```text
ping
```

### 5) Test Commands

#### Frontend

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\frontend\web"
pnpm lint
pnpm build
pnpm e2e   # Playwright (can backend + infra up)
```

#### Backend API

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\api"
python -m uv sync --all-groups
python -m uv run ruff check app tests
python -m uv run mypy app
python -m uv run pytest
```

#### Backend Worker

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker"
python -m uv sync --all-groups
python -m uv run ruff check . tests
python -m uv run mypy .
python -m uv run pytest
```

### 6) Quick Manual Test (Auth + Receipt Upload)

1. Start infra, API, frontend (va worker neu muon OCR queue consume).
2. Mo `http://localhost:3000/register`, tao tai khoan moi.
3. Dang nhap o `http://localhost:3000/login`.
4. Vao `http://localhost:3000/receipts/upload`, upload file JPG/PNG/PDF.
5. Xac nhan UI hien trang thai `uploading -> processing -> ready/failed`.
6. Neu failed/timeout, kiem tra fallback manual-entry message tren UI.

### 7) Environment Files

Copy env examples thanh `.env` (neu can custom gia tri local):

- `frontend/web/.env.example`
- `backend/api/.env.example`
- `backend/worker/.env.example`

### 8) Common Pitfall

- Neu chay uvicorn trong `backend/api/app` voi `main:app` se de loi import.
- Cach dung: chay tu `backend/api` voi `app.main:app` nhu lenh o tren.
- Khong dung `uv run uvicorn main:app --reload` trong `backend/api/app`.

### 9) Transaction APIs (Phase 3 baseline)

Sau khi dang nhap (cookie `pfa_session` da duoc set), co the goi:

- `POST /api/v1/transactions` - tao transaction (manual entry hoac tu OCR draft).
  Body toi thieu:

  ```json
  {
    "amount": "125000.00",
    "currency": "VND",
    "transaction_date": "2026-04-01",
    "merchant_name": "Pho 24",
    "category_id": 3,
    "note": "Lunch with team"
  }
  ```

  Optional `receipt_upload_id` de link voi receipt da OCR; phai thuoc cung user.

- `GET /api/v1/transactions` - list transaction co filter:

  | Query param | Mo ta |
  | --- | --- |
  | `start_date` | ISO date, transaction tu ngay nay tro di |
  | `end_date` | ISO date, transaction den het ngay nay |
  | `category_id` | Loc theo category, > 0 |
  | `merchant` | Substring match (case-insensitive) cho `merchant_name` |
  | `page` | Default `1`, >= 1 |
  | `size` | Default `20`, max `100` |

  Response shape:

  ```json
  {
    "items": [{ "id": 1, "amount": "125000.00", "...": "..." }],
    "meta": { "total": 42, "page": 1, "size": 20 }
  }
  ```

- `PUT /api/v1/transactions/{id}` - update partial (chi cac field gui len). Bao ve ownership + category access; neu update merchant + category, service tu dong remember mapping cho lan OCR sau.
- `DELETE /api/v1/transactions/{id}` - xoa transaction (return 204). Yeu cau ownership.

### 10) Dashboard Analytics API (Phase 4)

Sau khi dang nhap, goi:

- `GET /api/v1/dashboard/summary` - tra tong hop chi tieu cho 1 khoang thoi gian + so sanh ky truoc.

  Query params:

  | Query param | Mo ta |
  | --- | --- |
  | `range` | Preset: `7d` \| `30d` (default) \| `this_month` \| `last_month` \| `custom` |
  | `start_date` | ISO date, **bat buoc** khi `range=custom` |
  | `end_date` | ISO date, **bat buoc** khi `range=custom` |
  | `top_categories_limit` | Default `5`, max `20` |
  | `recent_transactions_limit` | Default `5`, max `50` |

  Response shape (rut gon):

  ```json
  {
    "range": { "preset": "30d", "start": "2026-03-27", "end": "2026-04-25", "days": 30 },
    "previous_range": { "preset": "30d", "start": "2026-02-25", "end": "2026-03-26", "days": 30 },
    "current":  { "total_spend": "400000.00", "transaction_count": 5 },
    "previous": { "total_spend": "165000.00", "transaction_count": 3 },
    "delta_amount":  "235000.00",
    "delta_percent": 142.42,
    "top_categories": [
      { "category_id": 1, "name": "An uong", "color": "#f59e0b", "total_amount": "185000.00", "transaction_count": 2, "percentage": 46.25 }
    ],
    "recent_transactions": [
      { "id": 12, "merchant_name": "Pho 24", "amount": "65000.00", "currency": "VND", "transaction_date": "2026-04-13", "category_id": 1, "category_name": "An uong" }
    ]
  }
  ```

  - `delta_percent` la `null` khi `previous.total_spend = 0` (khong the chia 0; UI render "-").
  - Giao dich khong co category gop vao nhom "Chua phan loai" trong `top_categories`.
  - Status code: `200` khi success (ke ca empty), `400` neu preset/custom invalid, `401` chua auth, `422` khi limit vuot cap.

## Current Status

- [x] Phase 0: Foundation
- [x] Phase 1: Auth and session
- [x] Phase 2: Receipt upload and OCR pipeline baseline
- [x] Phase 3: Transactions and review (manual entry + history + receipt review form)
- [x] Phase 4: Dashboard analytics (date_ranges + analytics service + summary API + UI shell + chart + previous period compare)
- [ ] Phase 5: Goals and budgets (planned)
- [x] Milestone M5: Tech debt cleanup (JWT fail-fast, lifespan broker, deep health check, S3/MinIO storage, SQLModel worker)
