# 9. Alembic migrations + Dependency matrix + Patterns

## 9.1 Migrations Alembic

### 9.1.1 `alembic/env.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/alembic/env.py:1-58
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from app.models import *  # noqa: F403
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

if database_url := os.getenv("DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
```

3 điểm quan trọng:

1. **`from app.models import *`**: load tất cả entity vào `SQLModel.metadata`. Vì entities re-export từ `pfa_shared.entities`, sau M5 metadata vẫn đầy đủ 7 table.

2. **DATABASE_URL override**: `if database_url := os.getenv("DATABASE_URL")` — runtime cho phép Docker compose / CI override URL khác `alembic.ini`.

3. **`compare_type=True`**: bật để Alembic detect type change (`String → Text`, `Integer → BigInteger`...). Tốn thêm thời gian autogenerate nhưng đáng để tránh schema drift.

### 9.1.2 `alembic.ini`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/alembic.ini:1-5
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = postgresql+psycopg://pfa:pfa@localhost:5432/pfa
```

`prepend_sys_path = .` đảm bảo `from app.models import *` work khi chạy `alembic` từ `backend/api/`.

### 9.1.3 Migration history (3 revisions)

```mermaid
gitGraph
    commit id: "init"
    commit id: "c9702a06526e<br/>create initial schema" tag: "8 tables"
    commit id: "f2a1bb149083<br/>add user profile defaults" tag: "currency/timezone/locale"
    commit id: "8ae8dfe4de39<br/>extend receipt upload metadata" tag: "file_size_bytes + error_*"
```

| Revision | Date | Mô tả |
|---|---|---|
| `c9702a06526e` | 2026-03-30 00:27 | Initial schema — tạo 7 table (`users`, `categories`, `insight_snapshots`, `receipt_uploads`, `budgets`, `ocr_results`, `transactions`, `user_merchant_mappings`) + indexes |
| `f2a1bb149083` | 2026-03-30 13:56 | Thêm `users.currency`, `users.timezone`, `users.locale` với server defaults VN |
| `8ae8dfe4de39` | 2026-03-30 15:30 | Thêm `receipt_uploads.file_size_bytes` + `error_code` + `error_message` |

Mỗi revision đều có cả `upgrade()` và `downgrade()` (rollback safe).

#### `c9702a06526e_create_initial_schema.py` (highlights)

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/alembic/versions/c9702a06526e_create_initial_schema.py:23-32
op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('password_hash', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('full_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
)
op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
```

`sqlmodel.sql.sqltypes.AutoString` là kiểu polymorphic của SQLModel — đổi sang `VARCHAR(n)` ở Postgres, `TEXT` ở SQLite.

`server_default=sa.text('(CURRENT_TIMESTAMP)')` cho `created_at` — cho phép caller insert mà không cần set `created_at`.

#### `f2a1bb149083_add_user_profile_defaults.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/alembic/versions/f2a1bb149083_add_user_profile_defaults.py:21-48
def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "currency",
            sqlmodel.sql.sqltypes.AutoString(length=10),
            nullable=False,
            server_default="VND",
        ),
    )
    op.add_column(
        "users",
        sa.Column("timezone", ..., server_default="Asia/Ho_Chi_Minh"),
    )
    op.add_column(
        "users",
        sa.Column("locale", ..., server_default="vi-VN"),
    )
```

Thêm 3 column NOT NULL với `server_default` → users hiện hữu được fill auto, không phải data migration thủ công.

#### `8ae8dfe4de39_extend_receipt_upload_metadata.py`

Pattern tương tự — thêm `file_size_bytes` (default 0) và 2 nullable column `error_code`, `error_message`.

### 9.1.4 Lệnh chạy migration

| Mục đích | Lệnh |
|---|---|
| Apply tất cả migration mới | `alembic upgrade head` |
| Tạo migration mới từ metadata diff | `alembic revision --autogenerate -m "msg"` |
| Rollback 1 revision | `alembic downgrade -1` |
| Xem history | `alembic history` |
| Stamp DB hiện tại = head | `alembic stamp head` |

### 9.1.5 Seed data sau migration

```bash
python -m uv run --project . python -m scripts.seed_categories
```

Insert 8 system categories (`Food, Transport, ...`) — idempotent nên chạy lại không tạo duplicate. Xem [`07-api-integrations.md`](./07-api-integrations.md) mục 7.6.

## 9.2 Ma trận dependency giữa các module

### 9.2.1 Import graph (rút gọn)

```mermaid
flowchart LR
    subgraph API["backend/api"]
        main["app.main"]
        api_routers["app.api.v1.*"]
        api_health["app.api.health"]
        api_deps["app.dependencies.auth"]
        api_core_cfg["app.core.config"]
        api_core_db["app.core.database"]
        api_core_log["app.core.logging"]
        api_core_sec["app.core.security"]
        api_mw["app.middleware.*"]
        api_models["app.models.entities"]
        api_schemas["app.schemas.*"]
        api_services["app.services.*"]
        api_integ["app.integrations.*"]
    end

    subgraph SHARED["backend/shared (pfa_shared)"]
        sh_entities["pfa_shared.entities"]
        sh_enums["pfa_shared.enums"]
        sh_config["pfa_shared.config"]
        sh_storage["pfa_shared.storage.*"]
        sh_schemas["pfa_shared.schemas"]
        sh_logging["pfa_shared.logging"]
        sh_utils["pfa_shared.utils"]
    end

    subgraph WORKER["backend/worker"]
        w_app["worker_app"]
        w_tasks["tasks"]
        w_ocr["ocr_provider"]
    end

    main --> api_core_cfg
    main --> api_core_log
    main --> api_mw
    main --> api_routers
    main --> api_services

    api_routers --> api_deps
    api_routers --> api_schemas
    api_routers --> api_services
    api_routers --> api_models
    api_routers --> api_core_db
    api_routers --> api_core_sec

    api_deps --> api_core_cfg
    api_deps --> api_core_sec
    api_deps --> api_models
    api_deps --> api_core_db

    api_services --> api_models
    api_services --> api_integ
    api_services --> api_core_cfg
    api_services --> api_core_log

    api_integ --> sh_storage
    api_models --> sh_entities
    api_health --> api_schemas

    api_core_log --> api_mw
    api_core_log --> api_core_cfg

    sh_entities --> sh_enums
    sh_storage --> sh_storage
    sh_config --> sh_enums
    sh_schemas --> sh_enums

    w_tasks --> w_app
    w_tasks --> w_ocr
    w_tasks --> sh_entities
    w_tasks --> sh_storage
    w_tasks --> sh_enums

    w_app --> sh_config
    w_app --> sh_logging

    classDef api fill:#e3f2fd,stroke:#1976d2
    classDef shared fill:#fff3e0,stroke:#f57c00
    classDef worker fill:#e8f5e9,stroke:#388e3c
    class main,api_routers,api_health,api_deps,api_core_cfg,api_core_db,api_core_log,api_core_sec,api_mw,api_models,api_schemas,api_services,api_integ api
    class sh_entities,sh_enums,sh_config,sh_storage,sh_schemas,sh_logging,sh_utils shared
    class w_app,w_tasks,w_ocr worker
```

### 9.2.2 Cross-package dependencies

| From | To | Purpose |
|---|---|---|
| `app.models.entities` | `pfa_shared.entities` | Re-export 7 table SQLModel |
| `app.integrations.storage.{base, local, s3}` | `pfa_shared.storage.*` | Re-export adapter |
| `app.integrations.storage.factory` | `pfa_shared.storage.build_storage_service` | Build adapter từ Settings |
| `app.api.health` | `pfa_shared.schemas.HealthResponse`, `pfa_shared.enums.ServiceName` | DTO `/health` |
| `app.services.ocr_queue` | `pfa_shared.config.CommonSettings` | Build broker (cùng Redis URL với worker) |
| `app.services.category_suggestion` | `pfa_shared.utils.normalize_whitespace` | Normalize merchant |
| `worker.tasks` | `pfa_shared.{entities, enums, storage}` | Toàn bộ data + storage |
| `worker.worker_app` | `pfa_shared.{config, logging}` | Settings + logger |

### 9.2.3 Layering rules

| Layer | Có thể import | KHÔNG được import |
|---|---|---|
| `app.core.*` | stdlib + `pfa_shared.*` + `pydantic` | `app.api.*`, `app.services.*` |
| `app.middleware.*` | `app.core.*` | `app.api.*`, `app.services.*` |
| `app.dependencies.*` | `app.core.*`, `app.models.*` | `app.api.*`, `app.services.*` |
| `app.models.*` | `pfa_shared.entities` | tất cả khác |
| `app.schemas.*` | stdlib + `pydantic` | `app.models.*`, `app.services.*` |
| `app.services.*` | `app.core.*`, `app.models.*`, `app.integrations.*` | `app.api.*` |
| `app.integrations.*` | `app.core.config`, `pfa_shared.*` | `app.services.*`, `app.api.*` |
| `app.api.*` | tất cả layer dưới | (không có gì cần tránh — đỉnh stack) |
| `worker.*` | `pfa_shared.*` | `app.*` (KHÔNG được import API code) |

Quy tắc số 1 (worker không import `app.*`) giải thích pattern proxy task ở `app/services/ocr_queue.py`: API đăng ký task có cùng tên với worker thay vì `import` task function từ worker.

## 9.3 Các pattern kiến trúc nổi bật

### 9.3.1 Adapter Pattern — Storage

`StorageService` Protocol + 2 impl (`Local`, `S3`) + factory. Test có thể inject `LocalStorageService(tmp_path)` cho integration test, production dùng `S3StorageService` qua `STORAGE_BACKEND=s3`.

### 9.3.2 Producer-Consumer qua Redis (TaskIQ)

```
API (Producer) ──kiq──▶ Redis Queue ──BLPOP──▶ Worker (Consumer)
```

API và Worker hoàn toàn decoupled — không có RPC, không có shared memory. Restart worker không ảnh hưởng API; ngược lại Redis down chỉ làm enqueue fail (API fall back qua `error_code=queue_unavailable`).

### 9.3.3 Proxy task pattern

API đăng ký task có cùng `task_name` với worker để dùng `broker.find_task(...).kiq(...)`, body proxy chỉ raise `NotImplementedError`. Tránh anti-pattern `sys.path.insert("../worker")` để import code worker.

### 9.3.4 Re-export pattern (M5 refactor)

`app.models.entities` và `app.integrations.storage.*` là alias cho `pfa_shared.entities` và `pfa_shared.storage.*`. Code routers/services cũ vẫn import qua đường cũ → backwards compat tuyệt đối.

### 9.3.5 Fail-fast Settings validator

`Settings._enforce_production_secrets` raise `ValueError` ngay trong `__init__` nếu staging/prod thiếu secret. App **không** boot được → CI catch sớm thay vì khám phá lúc runtime.

### 9.3.6 Fail-soft trên external dependency

`startup_ocr_broker` log warning nhưng return `False` thay vì raise → app vẫn boot khi Redis tạm down. Tương tự, `enqueue_ocr_job` return `False` cho caller rollback. Triết lý: **"Liveness ≠ Readiness"** — process có thể alive nhưng chưa ready.

### 9.3.7 Singleton qua `lru_cache`

`get_settings()`, `get_storage_service()`, `get_ocr_broker()` đều `@lru_cache(maxsize=1)`. Test phải `cache_clear()` khi monkeypatch (xem `conftest.py`).

### 9.3.8 ContextVar cho request_id

Mỗi async task có ContextVar riêng → `request_id` không bị share giữa request đồng thời. Logger factory tự động inject vào mọi `LogRecord` mà không cần code chỗ log truyền `extra={"request_id": ...}`.

### 9.3.9 Dataclass thay Pydantic cho service layer

Service trả `frozen=True, slots=True` dataclass (`DraftReviewData`, `DashboardSummary`, `CategoryBreakdown`, ...). Lý do:
- Không cần validation runtime (data đã trusted từ DB).
- Faster (không có ConfigDict overhead).
- Routers chịu trách nhiệm map sang Pydantic response → tách biệt domain model và transport model.

### 9.3.10 Idempotent operations

| Operation | Idempotency strategy |
|---|---|
| OCR worker retry | UPSERT `OcrResult` (UNIQUE constraint trên `receipt_upload_id`) |
| `remember_user_merchant_category` | UPSERT mapping |
| `LocalStorageService.delete` | No-op nếu file thiếu |
| `S3StorageService.delete` | S3 mặc định no-op |
| `seed_categories` | Skip nếu category đã tồn tại |
| Migration | Alembic version table track applied revisions |

### 9.3.11 Defense in depth — Upload validation

3 lớp check trong `validate_upload_file`:
1. Extension whitelist.
2. MIME whitelist.
3. Size cap.

Không dựa duy nhất vào client `Content-Type` (spoofable).

### 9.3.12 Anti-enumeration — 404 thay 403

`_ensure_receipt_owner`, `_ensure_transaction_owner`, `_ensure_category_accessible` đều trả 404 cho cả 2 case "không tồn tại" + "thuộc user khác". Tránh để attacker biết ID nào valid.

### 9.3.13 Anti user-enumeration — Generic login error

`POST /auth/login` luôn trả `Invalid email or password` cho cả 2 case "email không tồn tại" + "password sai". Attacker không thể enumerate account.

## 9.4 Tóm tắt văn hóa code

| Nguyên tắc | Biểu hiện trong code |
|---|---|
| Strict by default | `model_config = ConfigDict(extra="forbid")` ở mọi Pydantic schema |
| Fail-fast cho config | `_enforce_production_secrets` raise ngay khi load Settings |
| Fail-soft cho infra | Redis down → app vẫn boot; queue fail → endpoint trả 201 + error_code |
| Single source of truth | `pfa_shared.entities` cho ORM; `pfa_shared.storage` cho adapter |
| Dependency injection | FastAPI `Depends`, test override qua `app.dependency_overrides` |
| Comment đậm chất Việt + giải thích "tại sao" | Mọi file phức tạp đều có docstring tiếng Việt giải thích trade-off |
| Test pyramid | Unit (`build_ping_response`) → Integration (`run_ocr_for_receipt` với SQLite + LocalStorage) → API (TestClient với SQLite in-memory) |

---

**Hết tài liệu phân tích**. Để bổ sung phần frontend, infra Docker, CI workflow → tham khảo:
- `frontend/web/README.md`
- `infra/docker/docker-compose.yml`
- `.github/workflows/ci.yml`
