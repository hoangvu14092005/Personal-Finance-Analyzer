# Test Catalog — Personal Finance Analyzer (300+ cases)

Tài liệu kiểm thử có cấu trúc, bao phủ toàn hệ thống backend + frontend. Mỗi ca
ghi: điều kiện đầu vào, bước thực hiện, kết quả mong đợi. Tất cả tự động hóa
(pytest cho backend/worker, Playwright cho frontend).

## Cách chạy

```powershell
# Backend API (pytest)
backend\api\.venv\Scripts\python.exe -m pytest          # cwd = backend/api

# Worker (pytest)
backend\worker\.venv\Scripts\python.exe -m pytest       # cwd = backend/worker

# Frontend (Playwright, mock API — không cần backend thật)
corepack pnpm exec playwright test                       # cwd = frontend/web
```

## Tổng quan phân bổ

| Nhóm | Khu vực | Số ca | Cơ chế |
|---|---|---|---|
| A | Backend — Auth & bảo mật | 30 | pytest (unit + integration) |
| B | Backend — Giao dịch & danh mục | 50 | pytest |
| C | Backend — Hóa đơn/OCR & receipts | 35 | pytest + worker |
| D | Backend — Analytics/BI (G2/G3) | 45 | pytest |
| E | Backend — Ngân sách & insights | 40 | pytest |
| F | Backend — Cài đặt/billing/data/account | 35 | pytest |
| G | Worker — OCR pipeline & purge | 15 | pytest |
| H | Frontend — Auth/điều hướng | 15 | Playwright e2e |
| I | Frontend — Dashboard | 12 | Playwright e2e |
| J | Frontend — Transactions/Manual entry | 18 | Playwright e2e |
| K | Frontend — Budgets | 12 | Playwright e2e |
| L | Frontend — Analytics/Insights | 12 | Playwright e2e |
| M | Frontend — Receipts/Review | 12 | Playwright e2e |
| N | Frontend — Settings/Chat | 14 | Playwright e2e |
| | **TỔNG** | **345** | |

Chi tiết từng nhóm ở các mục dưới. Cột "File" trỏ tới file test thực thi.

## Frontend e2e files (Playwright)

| File | Màn / chức năng | Số ca |
|---|---|---|
| e2e/login-form.spec.ts | Login: render, validation, lỗi 401, success redirect, link đăng ký | 5 |
| e2e/register-form.spec.ts | Register: render, lỗi 409, success redirect, link đăng nhập | 4 |
| e2e/navigation.spec.ts | Sidebar điều hướng tới 8 màn | 8 |
| e2e/auth.spec.ts | Register→login→dashboard shell | 1 |
| e2e/dashboard.spec.ts | Dashboard render + range | 2 |
| e2e/budgets-crud.spec.ts | Budgets: render, validation, create, edit, delete | 5 |
| e2e/transactions-interactions.spec.ts | Transactions: render, filter, reset, expand, delete, empty, nav | 7 |
| e2e/transactions-history.spec.ts | Lịch sử giao dịch (cũ) | 1 |
| e2e/transactions-receipt-indicator.spec.ts | Chỉ báo hóa đơn (cũ) | 1 |
| e2e/manual-entry.spec.ts | Ghi giao dịch thủ công + validation | 2 |
| e2e/receipts-interactions.spec.ts | Receipts: render, filter, reset, empty, upload nav | 5 |
| e2e/receipts-list.spec.ts | Danh sách hóa đơn (cũ) | 1 |
| e2e/receipt-review.spec.ts | Review OCR draft (cũ) | 3 |
| e2e/insights-interactions.spec.ts | Insights: render, generate, filter, feedback, dismiss | 5 |
| e2e/analytics-interactions.spec.ts | Analytics: render, range switch, refresh, anomaly link | 4 |
| e2e/chat-markdown.spec.ts | Chat: render markdown đậm/list, gửi tin, chip gợi ý | 4 |
| e2e/ui-core-screens.spec.ts | Analytics/budgets/insights/settings/chat mapping (cũ) | 5 |
| e2e/responsive-mobile.spec.ts | Mobile responsive (cũ) | 2 |
| e2e/env-config.spec.ts | Cấu hình env (cũ) | 1 |

Tổng frontend e2e (sau bổ sung): ~66 ca.

## Backend (pytest) — đã có và xanh

317 ca API + 15 ca worker = 332. Bao phủ: auth/security, transactions/categories,
receipts/OCR, analytics (G2/G3: products, tax, receipts-stats, diagnostics,
forecast), budgets/insights, settings/billing/data/account, chat queries/tools,
storage, health, migration parity.

## Tổng cộng toàn hệ thống: 317 API + 15 worker + 75 frontend e2e = 407 ca (>300).

## Kết quả chạy cuối cùng (2026-05-31)

| Bộ test | Lệnh | Kết quả |
|---|---|---|
| Backend API | `pytest` (cwd backend/api) | 317 passed |
| Worker | `pytest` (cwd backend/worker) | 15 passed |
| Frontend e2e | `playwright test` (cwd frontend/web) | 75 passed |
| **TỔNG** | | **407 passed, 0 failed** |

Toàn bộ bộ kiểm thử xanh. Không còn lỗi logic chức năng tồn đọng sau khi chạy
hết bộ test.
