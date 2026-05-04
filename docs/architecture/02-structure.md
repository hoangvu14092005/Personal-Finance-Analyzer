# 2. Cấu trúc thư mục `backend/`

```
backend/
├── api/                           # FastAPI service (HTTP)
│   ├── alembic/                   # DB migrations (Alembic)
│   │   ├── env.py                 # Alembic runtime: load SQLModel metadata
│   │   ├── script.py.mako         # Template tạo migration mới
│   │   └── versions/              # 3 revisions tới hiện tại
│   ├── alembic.ini                # Alembic config (default DB url)
│   ├── app/                       # Application code
│   │   ├── main.py                # ⭐ FastAPI app + lifespan + middleware + router
│   │   ├── api/                   # HTTP routers
│   │   │   ├── health.py          #   /health, /health/live, /health/ready
│   │   │   └── v1/                #   API v1
│   │   │       ├── auth.py        #     /auth/{register,login,logout,me}
│   │   │       ├── categories.py  #     /categories (list)
│   │   │       ├── dashboard.py   #     /dashboard/summary
│   │   │       ├── receipts.py    #     /receipts/{upload, status, ocr-result, draft}
│   │   │       └── transactions.py#     /transactions CRUD + filter + paging
│   │   ├── core/                  # Cross-cutting concerns
│   │   │   ├── config.py          #   Settings (Pydantic Settings)
│   │   │   ├── database.py        #   SQLModel engine + get_session
│   │   │   ├── logging.py         #   configure_logging + LogRecord factory
│   │   │   └── security.py        #   JWT encode/decode + cookie helpers
│   │   ├── dependencies/          # FastAPI Depends targets
│   │   │   └── auth.py            #   get_current_user
│   │   ├── integrations/          # Adapter cho dịch vụ ngoài
│   │   │   ├── ocr/               #   OCR provider (Protocol + Mock + factory)
│   │   │   └── storage/           #   Storage adapter (re-export pfa_shared.storage)
│   │   ├── middleware/            # ASGI middleware
│   │   │   ├── request_context.py #   ContextVar request_id
│   │   │   └── request_id.py      #   Inject X-Request-ID + log start/end
│   │   ├── models/                # ORM entities (re-export pfa_shared.entities)
│   │   │   └── entities.py
│   │   ├── repos/                 # (rỗng, placeholder cho repository pattern)
│   │   ├── schemas/               # Pydantic DTO (request/response)
│   │   │   ├── auth.py
│   │   │   ├── categories.py
│   │   │   ├── dashboard.py
│   │   │   ├── health.py
│   │   │   ├── receipts.py
│   │   │   └── transactions.py
│   │   └── services/              # Business logic
│   │       ├── analytics.py             # Dashboard summary aggregation
│   │       ├── category_suggestion.py   # Suggest + remember mapping
│   │       ├── date_ranges.py           # Range presets + previous_period
│   │       ├── draft_review.py          # Build draft từ OCR JSON
│   │       ├── health_checks.py         # DB/Redis/S3 readiness probe
│   │       ├── ocr_queue.py             # TaskIQ producer (kiq)
│   │       ├── password_service.py      # pwdlib argon2 hash
│   │       └── receipt_validation.py    # MIME / size / extension check
│   ├── data/                      # storage_local_root mặc định
│   ├── scripts/
│   │   └── seed_categories.py     # CLI seed system categories
│   ├── tests/                     # Pytest (20+ test file)
│   │   └── conftest.py            #   Fixtures: SQLite in-memory, TestClient
│   ├── pyproject.toml             # uv + ruff + mypy + pytest config
│   ├── pyrightconfig.json
│   ├── alembic.ini
│   ├── .env.example
│   └── README.md
│
├── worker/                        # TaskIQ consumer
│   ├── worker_app.py              # broker init + settings load
│   ├── tasks.py                   # ⭐ ping_task + process_ocr_job + run_ocr_for_receipt
│   ├── ocr_provider.py            # Protocol OCRProvider + MockOCRProvider
│   ├── run_ping.py                # Manual dispatch ping_task để smoke test
│   ├── tests/
│   │   ├── test_ocr_provider.py
│   │   ├── test_ping_task.py
│   │   └── test_run_ocr_for_receipt.py
│   ├── pyproject.toml
│   ├── pyrightconfig.json
│   ├── .env.example
│   └── README.md
│
└── shared/                        # Library pfa_shared (single source of truth)
    └── pfa_shared/
        ├── __init__.py            # Re-export công khai
        ├── config.py              # CommonSettings (dataclass frozen)
        ├── entities.py            # ⭐ 7 SQLModel tables
        ├── enums.py               # AppEnv, ServiceName, ReceiptStatus
        ├── logging.py             # get_logger lightweight
        ├── schemas.py             # HealthResponse
        ├── utils.py               # normalize_whitespace
        └── storage/               # ⭐ Storage adapter dùng chung
            ├── __init__.py
            ├── base.py            #   StorageService Protocol + StoredObject
            ├── factory.py         #   build_storage_service(settings)
            ├── local.py           #   LocalStorageService (filesystem)
            └── s3.py              #   S3StorageService (boto3, MinIO/AWS)
```

## 2.1 Quy ước đặt tên

| Tầng | Quy ước | Ví dụ |
|---|---|---|
| Router | `app/api/v{N}/{resource}.py` | `app/api/v1/transactions.py` |
| Schema | `app/schemas/{resource}.py` (Pydantic, `extra="forbid"`) | `app/schemas/transactions.py` |
| Service | `app/services/{domain}.py` (thuần function/dataclass, không state) | `app/services/analytics.py` |
| Integration | `app/integrations/{adapter}/{base, factory, impl}.py` | `app/integrations/storage/factory.py` |
| Migration | `alembic/versions/{slug}_{description}.py` | `c9702a06526e_create_initial_schema.py` |

## 2.2 Workspace `uv` & dependency

`backend/api/pyproject.toml` và `backend/worker/pyproject.toml` đều khai báo:

```toml
[tool.uv.sources]
personal-finance-analyzer-shared = { path = "../shared" }
```

→ `pip install -e ../shared` ngầm định khi `uv sync`. Mọi thay đổi `pfa_shared` lập tức có hiệu lực ở cả 2 service mà không cần publish package.

`backend/shared/pyproject.toml` chỉ khai báo 2 dep "lõi": `pydantic>=2.9` và `sqlmodel>=0.0.22`. **Không** khai báo `boto3` để cho host package quyết định (lazy import trong `S3StorageService`).
