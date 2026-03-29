# progress_log.md

## Cách dùng
Sau **mỗi lần update thành công**, AI phải append một entry mới vào cuối file này để lưu trạng thái dự án. Mục tiêu là để lần làm việc tiếp theo AI đọc nhanh và biết chính xác dự án đang ở đâu.

## Format bắt buộc cho mỗi entry
```md
### YYYY-MM-DD HH:mm - <phase> - <short title>
- Goal:
- Files changed:
- What was implemented:
- Validation:
- Pending / Next:
- Risks / Notes:
```

## Prompt mẫu để yêu cầu AI tự ghi log
> Sau khi hoàn thành thay đổi, hãy append một entry mới vào `progress_log.md` theo đúng format chuẩn, tóm tắt chính xác những gì đã hoàn thành, cách đã validate, phần còn pending và bước tiếp theo đề xuất.

## Current status summary
- Trạng thái hiện tại: chỉ mới có tài liệu định hướng sản phẩm/PRD và bộ file ngữ cảnh cho vibecoding.
- Chưa có xác nhận codebase khởi tạo thật sự.
- Chưa có baseline repo, chưa có migrations, chưa có UI/API/worker implementation được xác nhận.

### 2026-03-14 00:00 - phase-0 - Initialize context pack
- Goal: Tạo bộ file ngữ cảnh để AI/dev có thể bắt đầu dự án đúng scope MVP.
- Files changed:
  - system_prompt.md
  - project_map.md
  - tech_stack.md
  - progress_log.md
  - roadmap.md
  - tasks/phase-0-foundation.md
  - tasks/phase-1-auth.md
  - tasks/phase-2-receipts-ocr.md
  - tasks/phase-3-transactions.md
  - tasks/phase-4-dashboard-analytics.md
  - tasks/phase-5-budgets.md
  - tasks/phase-6-ai-insights.md
  - tasks/phase-7-hardening-uat-release.md
  - tasks/phase-8-post-mvp.md
- What was implemented:
  - Chuẩn hóa scope MVP, project map, tech baseline và roadmap thực thi từ tài liệu sản phẩm/PRD.
  - Chia task theo phase để phục vụ vibecoding từng bước.
- Validation:
  - Đối chiếu nội dung với product spec và PRD đã upload.
  - Kiểm tra artifact markdown đã được tạo ra trong thư mục xuất.
- Pending / Next:
  - Khởi tạo repo monorepo và phase-0 foundation.
  - Chốt stack thực tế nếu team không dùng baseline đề xuất.
- Risks / Notes:
  - Version framework/library trong `tech_stack.md` là baseline đề xuất, không phải thông tin được chốt trong PRD.

### 2026-03-14 22:45 - phase-0 - Complete tasks 0.1 and 0.2
- Goal:
  - Hoàn thành foundation repo structure (0.1) và khởi tạo frontend Next.js skeleton (0.2).
- Files changed:
  - README.md
  - frontend/web/package.json
  - frontend/web/pnpm-lock.yaml
  - frontend/web/README.md
  - frontend/web/next.config.ts
  - frontend/web/tsconfig.json
  - frontend/web/eslint.config.mjs
  - frontend/web/postcss.config.mjs
  - frontend/web/next-env.d.ts
  - frontend/web/.gitignore
  - frontend/web/app/layout.tsx
  - frontend/web/app/page.tsx
  - frontend/web/app/health/page.tsx
  - frontend/web/app/globals.css
  - frontend/web/public/*
- What was implemented:
  - Tạo boundary thư mục chuẩn cho monorepo: frontend/web, backend/api, backend/worker, backend/shared, infra/docker, docs.
  - Tạo root README mô tả cấu trúc repo và lộ trình chạy local theo phase 0.
  - Khởi tạo app Next.js 15 App Router với TypeScript, Tailwind CSS, ESLint và package manager pnpm.
  - Thay landing mặc định bằng landing page cho dự án và tạo layout shell cơ bản (header/main/footer).
  - Thêm trang health check UI đơn giản tại route /health.
- Validation:
  - Kiểm tra cấu trúc thư mục bằng list directory, xác nhận boundary đúng yêu cầu 0.1.
  - Chạy `pnpm run lint` trong frontend/web: pass.
  - Chạy `pnpm run build` trong frontend/web: pass, route `/` và `/health` được generate thành công.
- Pending / Next:
  - Thực hiện task 0.3: khởi tạo backend API FastAPI bằng uv với endpoint GET /health.
  - Thực hiện task 0.4: khởi tạo worker TaskIQ + Redis broker.
  - Tiếp tục 0.5-0.6 để hoàn thiện shared package và local infra.
- Risks / Notes:
  - Máy ban đầu không nhận lệnh pnpm; đã xử lý bằng cài pnpm global để scaffold và install hoạt động ổn định.
  - `frontend/web/public/*` là nhóm file scaffold mặc định từ create-next-app.

### 2026-03-14 22:57 - phase-0 - Complete task 0.3 API skeleton
- Goal:
  - Khởi tạo backend API FastAPI theo cấu trúc chuẩn và dùng uv để quản lý dependencies.
- Files changed:
  - backend/api/pyproject.toml
  - backend/api/uv.lock
  - backend/api/README.md
  - backend/api/app/__init__.py
  - backend/api/app/main.py
  - backend/api/app/api/__init__.py
  - backend/api/app/api/health.py
  - backend/api/app/core/__init__.py
  - backend/api/app/models/__init__.py
  - backend/api/app/schemas/__init__.py
  - backend/api/app/services/__init__.py
  - backend/api/app/repos/__init__.py
- What was implemented:
  - Tạo cấu trúc FastAPI theo yêu cầu task 0.3: `app/main.py`, `app/api/`, `app/core/`, `app/models/`, `app/schemas/`, `app/services/`, `app/repos/`.
  - Khai báo project Python trong `pyproject.toml` với dependencies `fastapi` và `uvicorn[standard]`.
  - Dùng uv để sync dependencies và tạo lock file `uv.lock`.
  - Implement endpoint `GET /health` trả payload `{ "status": "ok", "service": "api" }`.
- Validation:
  - Chạy `python -m uv sync` tại `backend/api`: thành công.
  - Chạy server bằng uvicorn và gọi `http://127.0.0.1:8000/health`: trả payload đúng.
  - Kiểm tra status code bằng `Invoke-WebRequest`: trả `200`.
  - Kiểm tra lỗi editor cho `app/main.py` và `app/api/health.py`: không có lỗi.
- Pending / Next:
  - Task 0.4: khởi tạo worker TaskIQ với Redis broker và demo `ping_task`.
  - Task 0.5: chuẩn hóa shared Python package cho API/worker dùng chung.
  - Task 0.6: dựng local infra với PostgreSQL, Redis, MinIO.
- Risks / Notes:
  - Môi trường chưa có lệnh `uv` trong PATH hệ thống; hiện đang dùng `python -m uv` ổn định.
  - Lần chạy uvicorn đầu tiên lỗi import do working directory; đã khắc phục bằng `--app-dir` khi validate chạy nhanh.

### 2026-03-14 23:04 - phase-0 - Improve root run guide
- Goal:
  - Cập nhật README root để có hướng dẫn chạy local rõ ràng, copy-paste được ngay cho frontend và backend API.
- Files changed:
  - README.md
  - progress_log.md
- What was implemented:
  - Bổ sung mục `Local Run (Current)` trong README gồm prerequisites, lệnh chạy backend API, lệnh chạy frontend, URL kiểm tra nhanh và mục troubleshooting.
  - Nêu rõ lỗi thường gặp khi chạy uvicorn sai thư mục và cách chạy đúng.
  - Cập nhật lại `Current Status` để phản ánh đã hoàn thành task 0.2 và 0.3.
- Validation:
  - Đối chiếu lệnh trong README với cấu trúc thực tế của repository (`backend/api` và `frontend/web`).
  - Kiểm tra nội dung theo đúng trạng thái hiện tại của phase 0.
- Pending / Next:
  - Thực hiện task 0.4 (worker TaskIQ + Redis + ping_task).
  - Tiếp tục task 0.5-0.6 cho shared package và local infra.
- Risks / Notes:
  - Môi trường local có thể chưa có `uv` trong PATH; fallback an toàn là dùng `python -m uv`.

### 2026-03-14 23:08 - phase-0 - Fix backend run troubleshooting
- Goal:
  - Điều tra lỗi khi chạy theo README và cập nhật hướng dẫn để tránh lỗi import module khi start API.
- Files changed:
  - README.md
  - progress_log.md
- What was implemented:
  - Xác định nguyên nhân lỗi: chạy `uvicorn main:app` trong thư mục `backend/api/app` gây `ModuleNotFoundError: app`.
  - Cập nhật README thêm command an toàn dùng `--app-dir` tuyệt đối để có thể chạy từ mọi thư mục.
  - Bổ sung lưu ý không dùng `uv run uvicorn main:app --reload` trong `backend/api/app`.
- Validation:
  - Kiểm tra `python -m uv --version`: pass sau khi cài uv cho Python hiện tại.
  - Chạy `python -m uv sync`: pass.
  - Chạy API với command có `--app-dir`, gọi `/health` trả payload đúng và status code 200.
- Pending / Next:
  - Task 0.4: khởi tạo worker TaskIQ + Redis broker + demo ping_task.
  - Task 0.5-0.6: shared package và local infra.
- Risks / Notes:
  - Nếu shell đang dùng Python chưa cài uv thì cần chạy một lần: `python -m pip install --user uv`.

### 2026-03-14 23:37 - phase-0 - Add root gitignore baseline
- Goal:
  - Chuẩn bị file `.gitignore` tại root để tránh commit nhầm cache/build/secrets trong monorepo.
- Files changed:
  - .gitignore
  - progress_log.md
- What was implemented:
  - Tạo `.gitignore` root cho các nhóm: OS/editor, logs, `.env`, Node/Next frontend artifacts, Python/uv caches và virtual environments.
  - Giữ lại nguyên tắc track lock files và `.env.example` để đảm bảo reproducible setup.
  - Bổ sung rule dữ liệu local infra để chuẩn bị cho các task docker/compose tiếp theo.
- Validation:
  - Kiểm tra workspace hiện chỉ có `.gitignore` trong `frontend/web`; đã bổ sung thêm root `.gitignore` để phủ toàn repo.
  - Đối chiếu pattern với stack hiện tại (Next.js + FastAPI + uv).
- Pending / Next:
  - Thực hiện task 0.4 (worker TaskIQ + Redis broker + `ping_task`).
  - Khi thêm docker compose ở task 0.6, cập nhật thêm ignore cho volume/path thực tế nếu cần.
- Risks / Notes:
  - Nếu sau này cần commit file `.env` cho môi trường đặc biệt, phải điều chỉnh rule ignore rõ ràng theo thư mục thay vì bỏ global rule.

### 2026-03-16 23:59 - phase-0 - Complete task 0.4 worker TaskIQ
- Goal:
  - Hoàn thành task 0.4: khởi tạo worker TaskIQ dùng Redis broker và xác thực demo `ping_task` được consume end-to-end.
- Files changed:
  - backend/worker/pyproject.toml
  - backend/worker/uv.lock
  - backend/worker/worker_app.py
  - backend/worker/tasks.py
  - backend/worker/run_ping.py
  - backend/worker/README.md
  - README.md
  - progress_log.md
- What was implemented:
  - Khởi tạo worker Python project bằng uv tại `backend/worker` với dependencies `taskiq` và `taskiq-redis`.
  - Cấu hình Redis broker và Redis result backend trong `worker_app.py`, dùng `with_result_backend(...)` để tương thích API hiện tại.
  - Tạo demo task `ping_task` trong `tasks.py` và script dispatch `run_ping.py` để enqueue + wait result.
  - Chuẩn hóa lệnh chạy worker/dispatch trong README worker và README root bằng `uv run --project` + `--app-dir` để tránh lỗi import do working directory.
- Validation:
  - Chạy `python -m uv run --project "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" python -c "import taskiq, taskiq_redis; print('imports-ok')"`: pass.
  - Chạy Redis container local (`pfa-redis-dev`) và start worker bằng TaskIQ CLI: pass.
  - Chạy dispatch script `run_ping.py`: in ra `ping`.
  - Kiểm tra worker logs: có dòng `Executing task tasks:ping_task`.
- Pending / Next:
  - Thực hiện task 0.5: thiết lập `backend/shared` cho config/logging/enums/schemas/utils dùng chung API và worker.
  - Thực hiện task 0.6: docker-compose local infra đầy đủ (PostgreSQL, Redis, MinIO) và `.env.example` cho từng service.
- Risks / Notes:
  - TaskIQ worker startup phụ thuộc app dir; nếu chạy từ thư mục khác cần giữ tham số `--app-dir` như trong README.
  - Cần đảm bảo Redis local đang chạy trước khi dispatch task.

### 2026-03-29 15:25 - phase-0 - Complete task 0.5 shared package
- Goal:
  - Hoàn thành task 0.5: tạo shared Python package tại `backend/shared` để API và worker cùng dùng chung config, logging, enums, schemas và utility helpers.
- Files changed:
  - backend/shared/pyproject.toml
  - backend/shared/README.md
  - backend/shared/pfa_shared/__init__.py
  - backend/shared/pfa_shared/config.py
  - backend/shared/pfa_shared/enums.py
  - backend/shared/pfa_shared/schemas.py
  - backend/shared/pfa_shared/logging.py
  - backend/shared/pfa_shared/utils.py
  - backend/api/pyproject.toml
  - backend/api/app/api/health.py
  - backend/worker/pyproject.toml
  - backend/worker/worker_app.py
  - README.md
- What was implemented:
  - Khởi tạo package `personal-finance-analyzer-shared` với module import name `pfa_shared`.
  - Cung cấp `CommonSettings.from_env()` cho config dùng chung và chuẩn hóa enum môi trường/service (`AppEnv`, `ServiceName`).
  - Cung cấp schema Pydantic `HealthResponse` để chia sẻ contract response giữa service layers.
  - Cung cấp helper logger `get_logger(...)` và utility `normalize_whitespace(...)` làm baseline reusable.
  - Nối dependency local path vào API/worker qua `[tool.uv.sources]` để cả hai project import được package shared mà không cần publish package riêng.
  - Refactor `GET /health` của API dùng `HealthResponse` + `ServiceName.API` và refactor worker broker init dùng `CommonSettings` + shared logger.
- Validation:
  - Chạy `uv sync --project backend/api`: pass.
  - Chạy `uv sync --project backend/worker`: pass.
  - Chạy smoke check trong `backend/api`: import `app.api.health` và in `health_check().model_dump()` trả về status/service đúng.
  - Chạy smoke check trong `backend/worker`: import `worker_app.settings` và `ServiceName.WORKER`, in ra Redis URL và giá trị enum đúng.
- Pending / Next:
  - Bắt đầu task 0.6: dựng local infra bằng docker compose (PostgreSQL, Redis, MinIO).
  - Tạo `.env.example` cho frontend, API, worker để chuẩn hóa local onboarding.
- Risks / Notes:
  - `uv` hiển thị warning về `VIRTUAL_ENV` khác project venv path, nhưng dependency resolution và smoke checks đều pass.
  - Khi chạy quick Python checks cho API/worker cần chạy từ đúng project folder để tránh lỗi import module nội bộ (`app`, `worker_app`).

### 2026-03-29 15:30 - phase-0 - Align editor import resolution for shared package
- Goal:
  - Đồng bộ cấu hình editor để import `pfa_shared` trong worker không còn báo lỗi unresolved dù runtime đã pass.
- Files changed:
  - .vscode/settings.json
  - backend/worker/pyrightconfig.json
- What was implemented:
  - Thêm `python.analysis.extraPaths` trỏ tới `backend/shared` trong workspace settings.
  - Bổ sung `backend/worker/pyrightconfig.json` với `extraPaths` phù hợp cho context worker.
- Validation:
  - Re-check lỗi editor tại `backend/worker/worker_app.py`: không còn lỗi import `pfa_shared.*`.
- Pending / Next:
  - Chuyển sang task 0.6: local infra (PostgreSQL, Redis, MinIO) + `.env.example`.
- Risks / Notes:
  - Nếu đổi cấu trúc thư mục backend trong tương lai, cần cập nhật lại `extraPaths` tương ứng.

### 2026-03-30 09:10 - phase-0 - Continue task 0.6 infra validation
- Goal:
  - Hoàn thiện kiểm tra task 0.6 (local infra) sau khi đã có sẵn docker-compose, script init bucket và env examples.
- Files changed:
  - README.md
  - progress_log.md
- What was implemented:
  - Rà soát lại artifact 0.6 hiện có: `infra/docker/docker-compose.yml`, `infra/docker/scripts/minio-init.sh`, `backend/api/.env.example`, `backend/worker/.env.example`, `frontend/web/.env.example`.
  - Bổ sung note trong README yêu cầu Docker daemon/Docker Desktop phải chạy trước khi gọi `docker compose up -d`.
- Validation:
  - Chạy `docker compose config` tại `infra/docker`: pass, cấu hình được render đầy đủ.
  - Chạy `docker compose up -d`: fail do Docker engine chưa sẵn sàng (`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`).
  - Chạy `docker compose ps`: chưa có container chạy do lỗi engine.
- Pending / Next:
  - Khởi động Docker Desktop (hoặc Docker daemon), sau đó chạy lại:
    - `docker compose up -d`
    - `docker compose ps`
    - `docker compose logs minio-init`
  - Khi các service lên thành công, đánh dấu 0.6 done hoàn toàn.
- Risks / Notes:
  - Trạng thái hiện tại: artifact 0.6 đã có đủ; phần acceptance "services up" phụ thuộc môi trường Docker local.

### 2026-03-30 09:22 - phase-0 - Complete task 0.6 infra bring-up
- Goal:
  - Chạy và xác thực end-to-end local infra cho task 0.6 sau khi Docker daemon sẵn sàng.
- Files changed:
  - progress_log.md
- What was implemented:
  - Chạy `docker compose up -d` tại `infra/docker` để khởi động PostgreSQL, Redis, MinIO và `minio-init`.
  - Xử lý xung đột tên container cũ `pfa-redis-dev` (stopped) bằng `docker rm pfa-redis-dev`, sau đó bring-up lại thành công.
  - Theo dõi `docker compose logs minio-init` để xác nhận bucket `pfa-receipts` được tạo thành công.
- Validation:
  - `docker compose ps` hiển thị:
    - `pfa-postgres-dev`: healthy
    - `pfa-redis-dev`: healthy
    - `pfa-minio-dev`: up
  - `minio-init` log có dòng `Bucket initialization complete.`.
- Pending / Next:
  - Chuyển sang task 0.7 (database schema v1 + Alembic).
- Risks / Notes:
  - Khi đã xác nhận xong local infra, có thể dùng `docker compose down` để tắt services nếu không cần chạy nền.

### 2026-03-30 10:35 - phase-0 - Complete task 0.7 database schema v1
- Goal:
  - Hoàn thành task 0.7: thiết lập Alembic, tạo SQLModel entities v1, migration đầu tiên và seed category mặc định.
- Files changed:
  - backend/api/pyproject.toml
  - backend/api/app/core/database.py
  - backend/api/app/models/entities.py
  - backend/api/app/models/__init__.py
  - backend/api/alembic.ini
  - backend/api/alembic/env.py
  - backend/api/alembic/script.py.mako
  - backend/api/alembic/versions/c9702a06526e_create_initial_schema.py
  - backend/api/scripts/__init__.py
  - backend/api/scripts/seed_categories.py
  - backend/api/README.md
  - progress_log.md
- What was implemented:
  - Thêm dependencies database/migration cho API: `sqlmodel`, `alembic`, `psycopg[binary]`.
  - Tạo model SQLModel cho 8 entity lõi: `User`, `ReceiptUpload`, `OcrResult`, `Transaction`, `Category`, `Budget`, `InsightSnapshot`, `UserMerchantMapping`.
  - Thiết lập `app/core/database.py` với engine/session và URL mặc định PostgreSQL local.
  - Cấu hình Alembic (`alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`) dùng metadata từ SQLModel.
  - Tạo migration đầu tiên `c9702a06526e_create_initial_schema.py` bằng autogenerate.
  - Tạo seed script `scripts/seed_categories.py` với 8 category mặc định hệ thống.
- Validation:
  - `uv sync --project backend/api`: pass.
  - `alembic revision --autogenerate -m "create initial schema"`: pass (sinh revision đầu tiên).
  - `alembic upgrade head`: pass trên PostgreSQL qua container network (`Context impl PostgresqlImpl`, chạy upgrade tới revision đầu).
  - `python -m scripts.seed_categories`: pass, in ra `Seeded 8 default categories.`.
  - Query kiểm tra bằng `psql`: `total_categories = 8`.
- Pending / Next:
  - Task 0.8: config/settings/logging chuẩn và request correlation id baseline.
  - Task 0.9: quality baseline (ruff, mypy, pytest) và scripts check.
- Risks / Notes:
  - Từ host Windows có hiện tượng auth mismatch khi kết nối `localhost:5432`; workaround đã dùng là chạy migration/seed trong container cùng network `pfa-local-network`.
