# 3. Phân tích chi tiết — `backend/shared` (`pfa_shared`)

> Nguồn duy nhất cho entity, enum, storage adapter. Cả `api` và `worker` declare dependency này qua `[tool.uv.sources]` với path `../shared`.

## 3.1 `pfa_shared/__init__.py`

**Mục đích**: re-export public API.

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/shared/pfa_shared/__init__.py:1-13
"""Shared package exports for API and worker."""

from pfa_shared.config import CommonSettings 
from pfa_shared.enums import AppEnv, ServiceName
from pfa_shared.schemas import HealthResponse

__all__ = [
    "AppEnv",
    "CommonSettings",
    "HealthResponse",
    "ServiceName",
]
```

`__all__` công bố 4 symbol: `AppEnv`, `CommonSettings`, `HealthResponse`, `ServiceName`. Storage không re-export ở root mà dùng đường `pfa_shared.storage.*` trực tiếp.

## 3.2 `pfa_shared/enums.py`

3 enum kế thừa `StrEnum` để serialize JSON tự nhiên:

| Enum | Giá trị | Vai trò |
|---|---|---|
| `AppEnv` | `local`, `test`, `staging`, `prod` | Phân biệt môi trường để bật/tắt validation |
| `ServiceName` | `api`, `worker` | Trả trong `HealthResponse.service` |
| `ReceiptStatus` | `uploaded`, `processing`, `ready`, `failed` | State machine của `ReceiptUpload.status` |

**Hàm**: `AppEnv.from_value(value: str) -> AppEnv` — lookup case-insensitive, fallback `LOCAL` (dùng trong `CommonSettings.from_env`).

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/shared/pfa_shared/enums.py:12-18
@classmethod
def from_value(cls, value: str) -> "AppEnv":
    normalized = value.strip().lower()
    for member in cls:
        if member.value == normalized:
            return member
    return cls.LOCAL
```

## 3.3 `pfa_shared/config.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/shared/pfa_shared/config.py:18-40
@dataclass(frozen=True, slots=True)
class CommonSettings:
    """Config chung cho API và Worker. Đọc từ environment variables."""
    
    app_env: AppEnv
    log_level: str
    redis_url: str
    database_url: str
    
    s3_endpoint: str
    s3_region: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket_private: str
    storage_backend: Literal["local", "s3"]
    storage_local_root: str
    
    ocr_provider: str
    ocr_timeout_ms: int
    ocr_max_file_size_mb: int
```

**Tại sao dataclass thay vì Pydantic?** Comment trong file: lightweight, immutable (`frozen=True`), thread-safe (worker chia sẻ instance được), tiết kiệm RAM với `slots=True`. Worker không cần validation phức tạp như API (đã có `app/core/config.py` lo).

**Hàm `CommonSettings.from_env() -> CommonSettings`**: factory đọc `os.getenv(...)` từng field với default phù hợp local Docker Compose. `STORAGE_BACKEND` được normalize về `Literal["local", "s3"]` (mọi giá trị khác `s3` đều fallback `local`).

## 3.4 `pfa_shared/entities.py`

7 SQLModel tables, mỗi class kế thừa `SQLModel` với `table=True`. Comment đầu file khẳng định: **trước M5** entity sống ở `app/models/entities.py`, worker dùng raw SQL; **từ M5** unified ở đây.

| Entity | Table | Field nổi bật | Note |
|---|---|---|---|
| `User` | `users` | `email UNIQUE`, `password_hash`, `currency/timezone/locale` defaults VN | `created_at` server default `func.now()` |
| `ReceiptUpload` | `receipt_uploads` | `status`, `storage_key`, `error_code`, `error_message` | `status` string mapping `ReceiptStatus` (không enum trong DB) |
| `OcrResult` | `ocr_results` | `receipt_upload_id UNIQUE`, `normalized_payload` (JSON string) | 1-1 với receipt → worker UPSERT khi retry |
| `Category` | `categories` | `user_id NULL + is_system=True` = system; ngược lại user-owned | Index `name + is_system + user_id` |
| `Transaction` | `transactions` | `amount Numeric(12,2)`, FK soft sang category/receipt | Index `transaction_date` để filter range nhanh |
| `Budget` | `budgets` | `period_month` string `YYYY-MM` | Phase 5+ |
| `InsightSnapshot` | `insight_snapshots` | `*_json` chứa output LLM, `fingerprint` để dedupe | Phase 6+ |
| `UserMerchantMapping` | `user_merchant_mappings` | `normalized_merchant_name` (casefolded) | Cốt lõi cho category suggestion |

Mọi `created_at` dùng:

```python
created_at: datetime = Field(
    sa_column=Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
)
```

→ timestamp UTC từ DB, không phụ thuộc clock client.

**`Transaction.amount`** đặc biệt:

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/shared/pfa_shared/entities.py:110
amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
```

→ `Decimal` Python, `Numeric(12, 2)` Postgres → tránh floating point precision khi cộng tiền.

## 3.5 `pfa_shared/schemas.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/shared/pfa_shared/schemas.py:8-12
class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    service: ServiceName
```

Pydantic model duy nhất share giữa 2 service. `extra="forbid"` chặn field thừa lọt vào JSON response (nguyên tắc strict-by-default toàn dự án).

## 3.6 `pfa_shared/logging.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/shared/pfa_shared/logging.py:6-11
def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    return logging.getLogger(name)
```

Logger lightweight cho worker. API có version "đầy đủ" hơn ở `app/core/logging.py` (inject `request_id`).

## 3.7 `pfa_shared/utils.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/shared/pfa_shared/utils.py:4-5
def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())
```

Hàm tiện ích duy nhất — dùng trong `category_suggestion.normalize_merchant_name`.

## 3.8 `pfa_shared/storage/`

5 file tạo thành adapter pattern hoàn chỉnh.

### 3.8.1 `storage/base.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/shared/pfa_shared/storage/base.py:7-46
@dataclass(frozen=True, slots=True)
class StoredObject:
    storage_key: str
    size_bytes: int


class StorageNotFoundError(Exception):
    """Raise khi storage_key không tồn tại trên backend (404 / NoSuchKey)."""


class StorageService(Protocol):
    def upload_bytes(self, storage_key: str, content: bytes, content_type: str) -> StoredObject: ...
    def download_bytes(self, storage_key: str) -> bytes: ...
    def delete(self, storage_key: str) -> None: ...


class StorageSettings(Protocol):
    storage_backend: Literal["local", "s3"]
    storage_local_root: str
    s3_endpoint: str
    s3_region: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket_private: str
```

4 type chính:
- `StoredObject` — kết quả upload thành công (kèm size).
- `StorageNotFoundError` — exception thống nhất cho 2 backend (S3 raise `ClientError NoSuchKey`, local raise `FileNotFoundError` → adapter wrap về `StorageNotFoundError`).
- `StorageService` — Protocol structural typing. Caller có thể wrap sync API qua `asyncio.to_thread` nếu cần non-blocking.
- `StorageSettings` — Protocol mô tả các field cần. Cả `app.core.config.Settings` và `pfa_shared.config.CommonSettings` đều structural-match → factory không phụ thuộc cụ thể class nào.

### 3.8.2 `storage/local.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/shared/pfa_shared/storage/local.py:12-33
class LocalStorageService(StorageService):
    """Lưu file vào local filesystem dưới `root_dir`. Dùng cho dev/test."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir

    def upload_bytes(self, storage_key: str, content: bytes, content_type: str) -> StoredObject:
        file_path = self.root_dir / storage_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return StoredObject(storage_key=storage_key, size_bytes=len(content))

    def download_bytes(self, storage_key: str) -> bytes:
        file_path = self.root_dir / storage_key
        if not file_path.exists():
            raise StorageNotFoundError(f"storage_key not found: {storage_key}")
        return file_path.read_bytes()

    def delete(self, storage_key: str) -> None:
        file_path = self.root_dir / storage_key
        if file_path.exists():
            file_path.unlink()
```

3 hàm bám 1-1 vào Protocol:
- `upload_bytes`: tạo parent dirs nếu thiếu, ghi bytes, trả `StoredObject`. Bỏ qua `content_type` (filesystem không lưu metadata này — local mode dev only).
- `download_bytes`: đọc bytes; key thiếu → raise `StorageNotFoundError`.
- `delete`: idempotent (không raise nếu key thiếu).

### 3.8.3 `storage/s3.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/shared/pfa_shared/storage/s3.py:18-48
class S3StorageService(StorageService):
    def __init__(
        self,
        *,
        endpoint_url: str,
        region: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
    ) -> None:
        # Lazy import — package shared không declare boto3 dep, nhưng host
        # package (API hoặc worker) phải cài boto3 nếu dùng s3 backend.
        import boto3
        from botocore.client import Config
        ...
```

**Đặc điểm**:
- **Lazy import** `boto3`: shared không khai báo dep `boto3`; chỉ host package (`api`, `worker`) cài nếu dùng `STORAGE_BACKEND=s3`. Nhờ vậy unit test trong shared chạy không cần `boto3`.
- `endpoint_url` cho phép trỏ MinIO local lẫn AWS S3 thật.
- `signature_version="s3v4"` + retries 2 lần.
- `download_bytes` map `ClientError` code `NoSuchKey | 404` → `StorageNotFoundError`.
- `delete` để boto3 idempotent (S3 mặc định không raise nếu key thiếu).

### 3.8.4 `storage/factory.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/shared/pfa_shared/storage/factory.py:10-25
def build_storage_service(settings: StorageSettings) -> StorageService:
    if settings.storage_backend == "s3":
        return S3StorageService(
            endpoint_url=settings.s3_endpoint,
            region=settings.s3_region,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket_private,
        )
    return LocalStorageService(root_dir=Path(settings.storage_local_root))
```

Factory thuần stateless; caller (API/worker) tự cache singleton qua `lru_cache`.

### 3.8.5 `storage/__init__.py`

Re-export 7 symbol công khai: `LocalStorageService`, `S3StorageService`, `StorageNotFoundError`, `StorageService`, `StorageSettings`, `StoredObject`, `build_storage_service`.
