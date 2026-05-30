# Session Handoff — UI/API Demo Login

Date: 2026-05-29

## Current Purpose

Continue rebuilding Personal Finance Analyzer around the new domain/API logic while keeping the frontend close to the original `finance-analyzer-ui` visual language.

The user specifically asked to stop drifting away from `finance-analyzer-ui`, especially wording and presentation. The current frontend should feel like the original Vietnamese finance app, not a generic SaaS dashboard.

## Running Demo State

Use one frontend URL only:

```text
http://127.0.0.1:3005
```

Current demo backend behind it:

```text
http://127.0.0.1:8010
```

Temporary login for UI review:

```text
Tài khoản: admin
Mật khẩu: 1
```

Important: do not create more frontend ports unless necessary. The user explicitly complained that too many ports were created. Keep using `3005` for frontend.

## What Was Fixed Last

The user hit `Internal Server Error` on:

```text
http://127.0.0.1:3005/login?next=/dashboard
```

Root cause was broken Next dev cache in `frontend/web/.next`, with missing manifest files like:

```text
app-build-manifest.json
_buildManifest.js.tmp.*
```

Fix applied:

1. Stopped the frontend process on port `3005`.
2. Removed `frontend/web/.next`.
3. Removed `next/font/google` usage from `frontend/web/app/layout.tsx` because network-restricted Google Fonts caused instability/warnings.
4. Changed CSS font variables in `frontend/web/app/globals.css` to local/system fallbacks.
5. Restarted frontend on `3005` with:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8010'
corepack pnpm dev --hostname 127.0.0.1 --port 3005
```

Verified after fix:

```text
GET /login     -> 200
GET /dashboard -> 200
GET /budgets   -> 200
POST /api/v1/auth/login admin/1 -> 200
```

## Demo Auth Changes

Files changed for temporary demo login:

```text
frontend/web/app/login/page.tsx
backend/api/app/schemas/auth.py
backend/api/app/api/v1/auth.py
backend/api/scripts/seed_ui_demo.py
```

Behavior:

- Login form now accepts username/email text instead of email-only input.
- Backend login accepts short username/password for login only.
- Username `admin` maps to backend email `admin@example.com`.
- Register flow remains strict and still requires real email + strong password.
- `scripts.seed_ui_demo` creates/updates `admin@example.com` with password `1` and seeds demo data.

Seed command used:

```powershell
$env:DATABASE_URL='sqlite:///./.tmp/pfa-ui-demo.db'
$env:STORAGE_BACKEND='local'
.\.venv\Scripts\python.exe -m scripts.seed_ui_demo
```

Backend demo run command used:

```powershell
$env:DATABASE_URL='sqlite:///./.tmp/pfa-ui-demo.db'
$env:STORAGE_BACKEND='local'
$env:CORS_ORIGINS='http://localhost:3000,http://127.0.0.1:3000,http://localhost:3005,http://127.0.0.1:3005'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Why SQLite demo was used:

- Existing `localhost:8000` was occupied by a `fastapi` container but returned broken/closed connections.
- Existing Postgres on `5433` rejected `pfa/pfa` credentials.
- User wanted quick login, not infra debugging.

## UI Re-alignment Done

The frontend was pulled back toward `finance-analyzer-ui` style and copy.

Key direction:

- Keep Vietnamese app wording.
- Avoid generic SaaS copy such as `Command center`, `Source of truth`, `Workflow`, `Control center`.
- Prefer original labels like `Ví Thông Minh`, `Tổng quan`, `Phân tích chi tiêu`, `Sổ Nhật Ký Giao Dịch`, `Tự Động Trích Xuất Hóa Đơn (OCR Scan)`, `Quản lý ngân sách`, `Trợ lý tài chính (AI)`, `Cài Đặt Hệ Thống`.
- Use lucide icons like the original UI instead of text badges such as `AN`, `TX`, `ST`, `BG`, `OCR`.

High-visibility frontend files touched in this UI pass:

```text
frontend/web/components/layout/Nav.tsx
frontend/web/app/layout.tsx
frontend/web/app/globals.css
frontend/web/app/dashboard/dashboard-client.tsx
frontend/web/app/analytics/analytics-client.tsx
frontend/web/app/transactions/transaction-history-client.tsx
frontend/web/app/receipts/receipts-client.tsx
frontend/web/app/receipts/[id]/review/page.tsx
frontend/web/app/receipts/upload/page.tsx
frontend/web/app/budgets/budgets-client.tsx
frontend/web/app/chat/chat-client.tsx
frontend/web/app/settings/settings-client.tsx
```

Dependency added:

```text
lucide-react
```

## Verified Before Demo Login Changes

Before the later demo-login/font changes, the frontend passed:

```powershell
corepack pnpm build
.\node_modules\.bin\playwright.cmd test
```

Result at that point:

```text
28 passed
```

After demo-login/font changes, `/login`, `/dashboard`, `/receipts/upload`, and `/budgets` were smoke-tested through the running dev server and returned `200`. A full rebuild was not rerun after the final font/auth demo edits.

## Core Domain/API Rules To Preserve

Do not regress these decisions:

```text
Transaction = official financial record.
Receipt/Invoice = evidence/document record.
Dashboard/Budget/Analytics read confirmed transactions.
Receipt/OCR/Invoice screens read receipt_uploads, ocr_results, receipt_line_items, invoices, invoice_line_items.
OCR draft must be confirmed before it affects financial reports.
Receipt/Invoice remains after transaction is created.
```

Important date distinction:

```text
receipt_uploads.created_at = upload date
receipt_uploads.receipt_date = date printed/extracted from receipt
transactions.transaction_date = official spending date
transactions.confirmed_at = when user confirmed draft into transaction
```

## Current Caveats

- Demo login `admin / 1` is for local UI review only. Do not treat it as production auth.
- `backend/api/.tmp/pfa-ui-demo.db` is local demo state and should not become production source of truth.
- `frontend/web/.next` may need removal again if Next dev cache becomes inconsistent.
- In-app browser automation failed earlier with a Windows sandbox issue, so visual review is mostly user-driven through the open browser.
- Existing Docker/Postgres environment is inconsistent with `.env` credentials; avoid spending time there unless the next task is infra cleanup.

## Recommended Next Step

1. User should visually review `http://127.0.0.1:3005` after logging in with `admin / 1`.
2. Fix any UI screens that still differ too much from `finance-analyzer-ui`.
3. After visual approval, rerun:

```powershell
cd frontend/web
corepack pnpm build
.\node_modules\.bin\playwright.cmd test
```

4. Then decide whether to keep the local demo login behind an explicit dev flag or remove it before production hardening.
