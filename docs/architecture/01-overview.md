# 1. Tổng quan + Sơ đồ kiến trúc

## 1.1 Tổng quan hệ thống

Backend gồm **3 Python package** chia sẻ qua `uv` workspace:

| Package | Đường dẫn | Vai trò | Process |
|---|---|---|---|
| **API** | `backend/api/` | FastAPI HTTP service — auth, CRUD transaction, OCR upload, dashboard | `uvicorn app.main:app` |
| **Worker** | `backend/worker/` | TaskIQ consumer — chạy OCR job bất đồng bộ | `taskiq worker worker_app:broker` |
| **Shared** | `backend/shared/` | Library `pfa_shared` — entities, enums, config, storage adapter dùng chung | (library) |

**Hạ tầng phụ thuộc**: PostgreSQL (data), Redis (TaskIQ queue + result backend), MinIO/S3 (lưu ảnh hóa đơn). Mọi config tải từ environment variables.

**Điểm thiết kế chính**:
- API và Worker tách process riêng, giao tiếp **chỉ qua Redis queue** (TaskIQ) + **DB** (cùng schema). Không có RPC trực tiếp.
- `pfa_shared` là **single source of truth** cho entity và storage adapter (M5 refactor) — tránh drift schema giữa 2 service.
- API `lifespan` quản lý vòng đời broker; nếu Redis down thì app vẫn boot, endpoint upload **fail-soft** sang trạng thái `UPLOADED + error_code=queue_unavailable`.
- Storage adapter `local | s3` chọn theo env `STORAGE_BACKEND` — staging/prod **bắt buộc** `s3` (validate trong `Settings._enforce_production_secrets`).

## 1.2 Sơ đồ kiến trúc tổng thể

```mermaid
flowchart TB
    Client["🌐 Frontend Web<br/>(Next.js, port 3000)"]

    subgraph BackendProcesses["Backend processes"]
        direction TB
        subgraph APIProc["API Service (uvicorn :8000)"]
            direction TB
            MW["Middleware<br/>CORSMiddleware<br/>RequestIdMiddleware"]
            Routers["Routers<br/>/health, /api/v1/auth<br/>/api/v1/categories<br/>/api/v1/receipts<br/>/api/v1/transactions<br/>/api/v1/dashboard"]
            Deps["Dependencies<br/>get_session, get_current_user"]
            Services["Services<br/>analytics, date_ranges<br/>category_suggestion<br/>draft_review, ocr_queue<br/>password_service<br/>receipt_validation<br/>health_checks"]
            Integrations["Integrations<br/>storage (local/s3)<br/>ocr (mock)"]

            MW --> Routers --> Deps --> Services --> Integrations
        end

        subgraph WorkerProc["Worker Service (taskiq)"]
            direction TB
            Broker["worker_app.broker<br/>(ListQueueBroker)"]
            Tasks["tasks.py<br/>ping_task<br/>process_ocr_job"]
            OCRCore["run_ocr_for_receipt()<br/>(core logic)"]
            OCRProvider["ocr_provider.py<br/>MockOCRProvider"]
            Broker --> Tasks --> OCRCore
            OCRCore --> OCRProvider
        end
    end

    subgraph Shared["pfa_shared (library)"]
        direction LR
        Entities["entities.py<br/>(SQLModel tables)"]
        Enums["enums.py<br/>(AppEnv, ReceiptStatus)"]
        Config["config.py<br/>(CommonSettings)"]
        StorageAdapt["storage/<br/>(StorageService Protocol<br/>+ Local + S3)"]
        Schemas["schemas.py<br/>(HealthResponse)"]
    end

    subgraph Infra["Infrastructure"]
        direction LR
        Postgres[("🐘 PostgreSQL<br/>:5432")]
        Redis[("⚡ Redis<br/>:6379")]
        S3[("📦 MinIO/S3<br/>:9000")]
    end

    Client -- "HTTPS<br/>cookie pfa_session" --> MW
    MW -- "X-Request-ID" --> Client

    Services -. "import" .-> Shared
    Tasks -. "import" .-> Shared
    Integrations -. "re-export" .-> StorageAdapt

    Services -- "SQLModel session" --> Postgres
    Services -- "kiq enqueue" --> Redis
    Integrations -- "upload bytes" --> S3
    OCRCore -- "SQLModel session" --> Postgres
    OCRCore -- "download bytes" --> S3
    Broker -- "BLPOP queue" --> Redis

    classDef proc fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef shared fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef infra fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    class APIProc,WorkerProc proc
    class Shared shared
    class Infra infra
```

## 1.3 Layered architecture trong API service

```mermaid
flowchart TB
    L1["📡 Layer 1 — Edge<br/>main.py (FastAPI app, lifespan)<br/>Middleware: CORS + RequestId"]
    L2["🛣️ Layer 2 — Routing<br/>app/api/health.py<br/>app/api/v1/{auth, categories, receipts, transactions, dashboard}.py"]
    L3["🔐 Layer 3 — Dependencies<br/>app/dependencies/auth.py (get_current_user)<br/>app/core/database.py (get_session)"]
    L4["⚙️ Layer 4 — Services<br/>analytics, date_ranges, category_suggestion<br/>draft_review, receipt_validation<br/>password_service, ocr_queue, health_checks"]
    L5["🔌 Layer 5 — Integrations<br/>app/integrations/storage/* (re-export pfa_shared.storage)<br/>app/integrations/ocr/* (Protocol + factory + Mock)"]
    L6["🗃️ Layer 6 — Data<br/>app/models/entities.py (re-export pfa_shared.entities)<br/>SQLModel + Alembic migrations"]
    L7["🛠️ Layer 7 — Core<br/>app/core/{config, database, logging, security}.py<br/>app/middleware/{request_context, request_id}.py<br/>app/schemas/* (Pydantic DTO)"]

    L1 --> L2 --> L3 --> L4 --> L5
    L4 --> L6
    L2 --> L7
    L3 --> L7
    L4 --> L7
    L5 --> L7
```

## 1.4 Sơ đồ luồng dữ liệu — Upload hóa đơn → OCR → Review draft

```mermaid
sequenceDiagram
    autonumber
    participant FE as Frontend
    participant API as FastAPI
    participant Storage as Storage<br/>(local/S3)
    participant DB as PostgreSQL
    participant Q as Redis Queue
    participant W as Worker
    participant OCR as OCR Provider

    FE->>API: POST /api/v1/receipts/upload<br/>(multipart, cookie pfa_session)
    API->>API: get_current_user (JWT từ cookie)
    API->>API: validate_upload_file (ext, MIME, size)
    API->>Storage: upload_bytes(key, content, ct)
    Storage-->>API: StoredObject(storage_key, size)
    API->>DB: INSERT ReceiptUpload (status=PROCESSING)
    Note over API: Set PROCESSING TRƯỚC khi enqueue<br/>tránh race với worker
    API->>Q: kiq("tasks:process_ocr_job", receipt_id)
    alt enqueue thành công
        Q-->>API: ok
        API-->>FE: 201 {receipt_id, status: "processing"}
    else enqueue fail (Redis down)
        Q-->>API: exception
        API->>DB: UPDATE status=UPLOADED,<br/>error_code=queue_unavailable
        API-->>FE: 201 {receipt_id, status: "uploaded"}
    end

    par Worker xử lý song song
        Q->>W: BLPOP receipt_id
        W->>DB: SELECT ReceiptUpload (status→PROCESSING)
        W->>Storage: download_bytes(storage_key)
        Storage-->>W: bytes
        W->>OCR: extract_text(bytes, hint)
        OCR-->>W: OCRRawResult
        W->>OCR: normalize_receipt(raw)
        OCR-->>W: OCRNormalizedReceipt
        W->>DB: UPSERT OcrResult (status=READY)
        W->>DB: UPDATE ReceiptUpload (status=READY)
    end

    Note over FE: Polling status
    FE->>API: GET /api/v1/receipts/{id}
    API->>DB: SELECT ReceiptUpload
    API-->>FE: ReceiptStatusResponse

    FE->>API: GET /api/v1/receipts/{id}/draft
    API->>DB: SELECT ReceiptUpload + OcrResult
    API->>API: build_draft_review<br/>(parse JSON, suggest category)
    API->>DB: SELECT UserMerchantMapping
    API-->>FE: DraftReviewResponse
```

## 1.5 Sơ đồ luồng — Tạo transaction + học mapping merchant

```mermaid
sequenceDiagram
    autonumber
    participant FE as Frontend
    participant API as FastAPI
    participant DB as PostgreSQL

    FE->>API: POST /api/v1/transactions<br/>{amount, merchant_name, category_id, ...}
    API->>API: get_current_user
    API->>DB: SELECT ReceiptUpload (validate ownership)
    alt category_id provided
        API->>DB: SELECT Category (validate accessible)
    else không có category_id
        API->>DB: SELECT UserMerchantMapping<br/>(suggest_category_for_merchant)
        DB-->>API: category_id | None
    end
    API->>DB: INSERT Transaction
    alt user provide cả merchant + category
        API->>DB: UPSERT UserMerchantMapping<br/>(remember_user_merchant_category)
        Note over DB: Lần upload sau có cùng merchant<br/>→ suggest đúng category
    end
    API-->>FE: 201 TransactionResponse
```

## 1.6 Sơ đồ luồng — Dashboard summary

```mermaid
sequenceDiagram
    autonumber
    participant FE as Frontend
    participant API as FastAPI
    participant DB as PostgreSQL

    FE->>API: GET /api/v1/dashboard/summary?range=30d
    API->>API: get_current_user
    API->>API: RangePreset(range) — parse enum
    API->>API: resolve_range(preset) → DateRange(current)
    API->>API: previous_period(current, preset) → DateRange(previous)
    API->>API: compute_summary(...) — 4 queries:
    API->>DB: SUM+COUNT current period
    API->>DB: SUM+COUNT previous period
    API->>DB: GROUP BY category (top N)
    API->>DB: SELECT recent transactions JOIN category
    API->>API: Tính delta_amount, delta_percent,<br/>percentage cho mỗi category
    API-->>FE: DashboardSummaryResponse
```

## 1.7 Sơ đồ luồng — Readiness check (`/health/ready`)

```mermaid
sequenceDiagram
    autonumber
    participant LB as Load Balancer / K8s
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Redis as Redis
    participant S3 as MinIO/S3

    LB->>API: GET /health/ready
    par 3 check song song
        API->>DB: SELECT 1 (timeout 2s)
        API->>Redis: PING (timeout 2s)
        API->>S3: head_bucket (timeout 4s, chỉ khi backend=s3)
    end
    DB-->>API: ok | error
    Redis-->>API: ok | error
    S3-->>API: ok | error | skipped(local)

    alt all ok
        API-->>LB: 200 {status: "ok", components: [...]}
    else có 1 component down
        API-->>LB: 503 {status: "degraded", components: [...]}
    end
```

## 1.8 Mô hình dữ liệu (ERD)

```mermaid
erDiagram
    USERS ||--o{ RECEIPT_UPLOADS : owns
    USERS ||--o{ TRANSACTIONS : owns
    USERS ||--o{ CATEGORIES : "owns (custom)"
    USERS ||--o{ BUDGETS : owns
    USERS ||--o{ INSIGHT_SNAPSHOTS : owns
    USERS ||--o{ USER_MERCHANT_MAPPINGS : owns

    RECEIPT_UPLOADS ||--o| OCR_RESULTS : "has 1 (UNIQUE)"
    RECEIPT_UPLOADS ||--o{ TRANSACTIONS : "linked from"

    CATEGORIES ||--o{ TRANSACTIONS : categorizes
    CATEGORIES ||--o{ BUDGETS : "scoped to"
    CATEGORIES ||--o{ USER_MERCHANT_MAPPINGS : "predicts"

    USERS {
        int id PK
        string email UK "max 255"
        string password_hash "argon2"
        string full_name "nullable"
        string currency "default VND"
        string timezone "default Asia/Ho_Chi_Minh"
        string locale "default vi-VN"
        bool is_active "default true"
        datetime created_at
    }
    RECEIPT_UPLOADS {
        int id PK
        int user_id FK
        string file_name
        string content_type
        int file_size_bytes
        string storage_key
        string status "uploaded|processing|ready|failed"
        string error_code "nullable"
        string error_message "nullable"
        datetime created_at
    }
    OCR_RESULTS {
        int id PK
        int receipt_upload_id FK,UK
        string provider
        string raw_text "nullable"
        float confidence "nullable"
        string normalized_payload "JSON string"
        string status
        datetime created_at
    }
    CATEGORIES {
        int id PK
        int user_id "FK nullable (NULL=system)"
        string name
        string color "nullable"
        bool is_system "default false"
        datetime created_at
    }
    TRANSACTIONS {
        int id PK
        int user_id FK
        int category_id "FK nullable"
        int receipt_upload_id "FK nullable"
        string merchant_name "nullable"
        decimal amount "Numeric(12,2)"
        string currency "default VND"
        date transaction_date
        string note "nullable"
        datetime created_at
    }
    BUDGETS {
        int id PK
        int user_id FK
        int category_id FK
        string period_month "YYYY-MM"
        decimal amount "Numeric(12,2)"
        datetime created_at
    }
    INSIGHT_SNAPSHOTS {
        int id PK
        int user_id FK
        date range_start
        date range_end
        string insights_json
        string recommendations_json
        string alerts_json
        string fingerprint
        datetime created_at
    }
    USER_MERCHANT_MAPPINGS {
        int id PK
        int user_id FK
        string raw_merchant_name
        string normalized_merchant_name "casefolded"
        int category_id "FK nullable"
        float confidence "nullable"
        datetime created_at
    }
```

**Constraint nổi bật**:
- `users.email` `UNIQUE` index → register check duplicate.
- `ocr_results.receipt_upload_id` `UNIQUE` → mỗi receipt có nhiều nhất 1 OCR result; worker dùng UPSERT để retry idempotent.
- `categories.user_id NULL + is_system=True` → system seed; user-defined có `user_id != NULL + is_system=False`.
- `transactions.amount Numeric(12,2)` → tránh float precision; max 999_999_999.99.
