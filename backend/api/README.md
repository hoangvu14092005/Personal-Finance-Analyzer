# Backend API

FastAPI service for Personal Finance Analyzer.

## Run local

> **Quan trọng:** Schema database được quản lý hoàn toàn bằng Alembic (source of
> truth). App KHÔNG còn tự tạo bảng lúc khởi động. Trên một DB mới, bạn PHẢI chạy
> `alembic upgrade head` TRƯỚC khi start uvicorn — nếu quên, app vẫn start nhưng
> mọi truy vấn sẽ lỗi `relation does not exist`.

```bash
python -m uv sync
python -m uv run --project . alembic upgrade head
python -m uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Health check

- Endpoint: `GET /health`
- Expected response:

```json
{
  "status": "ok",
  "service": "api"
}
```

## Database migrations (Task 0.7)

Apply migration on the default local DB URL:

```bash
python -m uv run --project . alembic upgrade head
```

Create a new migration revision from SQLModel metadata:

```bash
python -m uv run --project . alembic revision --autogenerate -m "your message"
```

Seed default categories:

```bash
python -m uv run --project . python -m scripts.seed_categories
```

If host-to-Docker PostgreSQL auth is blocked locally, run migration from a temporary container in the same Docker network:

```bash
docker run --rm --network pfa-local-network -v "${PWD}:/workspace" -w /workspace/backend/api python:3.12-slim sh -lc "pip install --no-cache-dir alembic sqlmodel 'psycopg[binary]' >/tmp/pip.log 2>&1 && DATABASE_URL='postgresql+psycopg://pfa:pfa@postgres:5432/pfa' alembic upgrade head"
```

## Quality checks (Task 0.9)

Install dev dependencies:

```bash
python -m uv sync --all-groups
```

Run lint, typecheck, tests:

```bash
python -m uv run ruff check app tests
python -m uv run mypy app
python -m uv run pytest
```

## Run against real Postgres (không dùng SQLite demo)

Nguồn cấu hình duy nhất là `../../.env` (root). Mặc định đã trỏ Postgres thật:
`DATABASE_URL=postgresql+psycopg://pfa:pfa@localhost:5433/pfa`. SQLite demo
(`pfa-ui-demo.db`, port 8010) chỉ là override thủ công khi review nhanh — KHÔNG
dùng cho phát triển nghiêm túc.

Quy trình chuẩn:

```bash
# 1. Khởi động infra (Postgres + Redis + MinIO)
docker compose -f ../../infra/docker/docker-compose.yml up -d

# 2. Tạo schema (Alembic là source of truth)
python -m uv run --project . alembic upgrade head

# 3. Seed dữ liệu khởi tạo
python -m uv run --project . python -m scripts.seed_categories
# (tùy chọn) seed tài khoản demo + dữ liệu mẫu cho review UI
python -m uv run --project . python -m scripts.seed_ui_demo

# 4. Chạy API trên Postgres thật
python -m uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **Lệch credential thường gặp:** nếu container Postgres báo `password
> authentication failed`, nguyên nhân phổ biến là volume cũ `infra/docker/.data/postgres`
> được tạo với mật khẩu khác `.env` hiện tại. Postgres chỉ áp `POSTGRES_PASSWORD`
> khi khởi tạo volume lần đầu. Xử lý: dừng stack, xóa volume cũ rồi bring-up lại
> (CHỈ làm khi chấp nhận mất dữ liệu local):
>
> ```bash
> docker compose -f ../../infra/docker/docker-compose.yml down
> # xóa thư mục infra/docker/.data/postgres rồi up lại
> docker compose -f ../../infra/docker/docker-compose.yml up -d
> ```

> **Demo login:** username `admin` / mật khẩu `1` chỉ hoạt động khi
> `ENABLE_DEMO_LOGIN=true` trong `.env` (local). Staging/prod ép tắt qua
> config validator.

