# Personal Finance Analyzer

Ứng dụng quản lý chi tiêu cá nhân với AI: upload hóa đơn → OCR tự động → chatbot hỏi đáp tiếng Việt.

## Cần cài trước

- Docker Desktop
- Python 3.13
- Node.js 20+ (có pnpm qua `corepack enable`)
- LLM endpoint chạy tại `http://localhost:20128/v1`

## Setup lần đầu

Tất cả cấu hình môi trường hiện nằm ở **root `.env`**. Khi clone mới, tạo file này từ template:

```cmd
copy .env.example .env
```

Sau đó chỉ sửa `D:\VuLapTrinh2\Personal_Finance_Analyzer\.env` cho toàn bộ stack: Docker, API, Worker và Frontend.

```cmd
:: 1. Start Docker
cd /d D:\VuLapTrinh2\Personal_Finance_Analyzer\infra\docker
docker compose --env-file ..\..\.env up -d

:: 2. Tạo venv + cài packages
cd /d D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\api
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ..\shared
.\.venv\Scripts\python.exe -m pip install -e .

:: 3. Tạo database tables
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.seed_categories

:: 4. Cài frontend
cd /d D:\VuLapTrinh2\Personal_Finance_Analyzer\frontend\web
corepack pnpm install
```

## Chạy hàng ngày

Cần 4 terminal. Mỗi terminal mở CMD riêng, gõ lệnh tương ứng:

**Terminal 1 — Docker** (chạy 1 lần, để yên):
```cmd
cd /d D:\VuLapTrinh2\Personal_Finance_Analyzer\infra\docker
docker compose --env-file ..\..\.env up -d
```

**Terminal 2 — Backend API** (bắt buộc):
```cmd
cd /d D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 3 — Worker** (cần cho OCR + chat):
```cmd
cd /d D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker
..\api\.venv\Scripts\python.exe -m taskiq worker --app-dir . worker_app:broker tasks index_tasks
```

**Terminal 4 — Frontend** (bắt buộc):
```cmd
cd /d D:\VuLapTrinh2\Personal_Finance_Analyzer\frontend\web
corepack pnpm dev
```

**Tóm tắt:**
- Muốn dùng web → cần Terminal 1 + 2 + 4
- Muốn upload receipt + chat AI → cần cả 4

## Mở app

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (minioadmin / minioadmin)

## Test nhanh

1. Mở http://localhost:3000 → Đăng ký → Đăng nhập
2. Upload hóa đơn → đợi OCR → review → lưu
3. Vào /chat → hỏi "Tháng này tôi tiêu bao nhiêu?"

## Lỗi thường gặp

| Lỗi | Fix |
|---|---|
| API crash thiếu module | Chạy lại: `.\.venv\Scripts\python.exe -m pip install -e ..\shared -e .` |
| CORS 400 Bad Request | Sửa root `.env`: `CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000` rồi restart API |
| DB connection refused | Docker chưa up. Chạy `docker compose --env-file ..\..\.env up -d` trong `infra\docker` |
| Port 5432 conflict | Project dùng port **5433**. Check root `.env` có `localhost:5433` |
| Worker không OCR | Check root `.env` có `OCR_PROVIDER=llm_vision` và `CHAT_LLM_*` |
| Frontend "Failed to fetch" | Check root `.env` có `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` |
