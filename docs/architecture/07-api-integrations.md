# 7. Phân tích chi tiết — `app/{integrations, schemas, models}` + `tests`, `scripts`

## 7.1 `app/integrations/`

### 7.1.1 `integrations/storage/`

Re-export pattern — toàn bộ implementation nằm ở `pfa_shared.storage` (xem `03-shared.md` mục 3.8). Lý do: code API cũ trước M5 import từ `app.integrations.storage.base` → giữ path để khỏi đổi import diện rộng.

#### `storage/__init__.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/integrations/storage/__init__.py:1-18
from app.integrations.storage.base import (
    StorageNotFoundError,
    StorageService,
    StoredObject,
)
from app.integrations.storage.factory import get_storage_service
from app.integrations.storage.local import LocalStorageService
from app.integrations.storage.s3 import S3StorageService
```

#### `storage/base.py` / `local.py` / `s3.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/integrations/storage/base.py:1-13
"""Re-export storage primitives từ `pfa_shared.storage` (M5)."""
from pfa_shared.storage.base import (
    StorageNotFoundError,
    StorageService,
    StoredObject,
)
```

`local.py` re-export `LocalStorageService`, `s3.py` re-export `S3StorageService`. Mỗi file 7 dòng — chỉ là alias.

#### `storage/factory.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/integrations/storage/factory.py:1-17
from functools import lru_cache

from app.core.config import get_settings
from pfa_shared.storage import StorageService, build_storage_service


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    """Trả về implementation `StorageService` theo `settings.storage_backend`.

    Cache singleton qua `lru_cache`. Khi đổi settings trong test, gọi
    `get_storage_service.cache_clear()`.
    """
    return build_storage_service(get_settings())
```

Lý do dùng `lru_cache`:
- Tạo `S3StorageService` cần boto3 init (chậm) → chỉ chạy 1 lần.
- `LocalStorageService` không expensive nhưng cũng giữ singleton để consistent.
- Test phải `cache_clear()` khi monkeypatch settings (xem `conftest.py`).

### 7.1.2 `integrations/ocr/`

#### `ocr/base.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/integrations/ocr/base.py:1-30
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OCRRawResult:
    provider: str
    raw_text: str
    confidence: float


@dataclass(frozen=True, slots=True)
class OCRNormalizedReceipt:
    merchant: str
    transaction_date: str
    total_amount: Decimal
    currency: str


class OCRProvider(Protocol):
    def extract_text(self, file_path: Path) -> OCRRawResult: ...
    def normalize_receipt(self, raw: OCRRawResult) -> OCRNormalizedReceipt: ...
```

⚠️ **Note quan trọng**: API integration vẫn còn signature cũ `extract_text(file_path: Path)` (trước M5). Worker đã refactor sang `extract_text(content: bytes, source_hint: str)` (xem `08-worker.md`). Do API hiện không thực sự gọi OCR trực tiếp (chỉ enqueue task → worker chạy), inconsistency này không gây lỗi runtime, nhưng nên đồng nhất ở refactor sau.

#### `ocr/mock.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/integrations/ocr/mock.py:1-23
class MockOCRProvider(OCRProvider):
    def extract_text(self, file_path: Path) -> OCRRawResult:
        return OCRRawResult(
            provider="mock",
            raw_text=f"Receipt extracted from {file_path.name}",
            confidence=0.91,
        )

    def normalize_receipt(self, raw: OCRRawResult) -> OCRNormalizedReceipt:
        return OCRNormalizedReceipt(
            merchant="Mock Mart",
            transaction_date="2026-03-30",
            total_amount=Decimal("125000.00"),
            currency="VND",
        )
```

Mock trả fixture cố định để test dashboard/transaction không cần OCR thật.

#### `ocr/factory.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/integrations/ocr/factory.py:1-23
_PROVIDER_REGISTRY: dict[str, type[OCRProvider]] = {
    "mock": MockOCRProvider,
}


def get_ocr_provider() -> OCRProvider:
    """Trả về implementation `OCRProvider` theo `settings.ocr_provider`.

    Fallback về `MockOCRProvider` nếu cấu hình không khớp registry để giữ
    pipeline OCR hoạt động được trong dev local kể cả khi env config sai.
    """
    settings = get_settings()
    provider_cls = _PROVIDER_REGISTRY.get(settings.ocr_provider, MockOCRProvider)
    return provider_cls()
```

Registry pattern — thêm provider thật (PaddleOCR/EasyOCR/Vision API) chỉ cần thêm entry vào dict, không phải sửa if-else.

#### `ocr/__init__.py`

Re-export 4 symbol: `OCRNormalizedReceipt`, `OCRProvider`, `OCRRawResult`, `get_ocr_provider`.

## 7.2 `app/schemas/`

> Pydantic DTO cho request/response. Mọi schema dùng `model_config = ConfigDict(extra="forbid")` để chặn field không hợp lệ — nguyên tắc strict-by-default.

### 7.2.1 `schemas/auth.py`

| Class | Vai trò |
|---|---|
| `RegisterRequest` | Body POST /auth/register |
| `LoginRequest` | Body POST /auth/login |
| `ProfileResponse` | DTO user profile |
| `AuthResponse` | Wrapper `{user: ProfileResponse}` |

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/schemas/auth.py:6-23
class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    currency: str = Field(default="VND", min_length=3, max_length=10)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", max_length=64)
    locale: str = Field(default="vi-VN", max_length=16)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        has_alpha = any(ch.isalpha() for ch in value)
        has_digit = any(ch.isdigit() for ch in value)
        if not has_alpha or not has_digit:
            raise ValueError("Password must include both letters and digits")
        return value
```

Validator `validate_password_strength` chỉ check baseline (alpha + digit). Đủ cho MVP — production có thể nâng lên zxcvbn.

### 7.2.2 `schemas/categories.py`

```python
class CategoryResponse(BaseModel):
    id: int
    name: str
    color: str | None
    is_system: bool
    user_id: int | None
    created_at: datetime


class CategoryListResponse(BaseModel):
    items: list[CategoryResponse]
```

### 7.2.3 `schemas/dashboard.py`

5 model:

| Model | Vai trò |
|---|---|
| `RangeInfo` | `{preset, start, end, days}` |
| `CategoryBreakdownResponse` | 1 dòng top categories |
| `RecentTransactionResponse` | 1 dòng recent list |
| `PeriodTotalsResponse` | `{total_spend, transaction_count}` |
| `DashboardSummaryResponse` | Wrapper toàn bộ payload |

Lưu ý: `delta_percent: float | None` — nullable cho case previous = 0.

### 7.2.4 `schemas/health.py`

```python
class ComponentStatus(BaseModel):
    name: str
    status: Literal["ok", "down"]
    error: str | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    components: list[ComponentStatus]
```

`Literal` thay vì plain `str` để OpenAPI schema rõ enum.

### 7.2.5 `schemas/receipts.py`

4 model — mỗi endpoint 1 response:

| Endpoint | Schema |
|---|---|
| `POST /upload` | `ReceiptUploadResponse {receipt_id, status}` |
| `GET /{id}` | `ReceiptStatusResponse` |
| `GET /{id}/ocr-result` | `OcrResultResponse` |
| `GET /{id}/draft` | `DraftReviewResponse` |

`DraftReviewResponse` là payload phức tạp nhất với 9 field, mọi field đều nullable trừ `receipt_id, receipt_status, provider`.

### 7.2.6 `schemas/transactions.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/schemas/transactions.py:9-32
class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(..., gt=Decimal("0"), max_digits=12, decimal_places=2)
    currency: str = Field(default="VND", min_length=3, max_length=10)
    transaction_date: date
    merchant_name: str | None = Field(default=None, max_length=255)
    category_id: int | None = Field(default=None, gt=0)
    receipt_upload_id: int | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("merchant_name", "note")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None
```

5 model:
- `TransactionCreate` — body POST. Constraints: `amount > 0`, `Decimal(12,2)`, `category_id > 0` (nếu có), validators normalize currency uppercase + trim text.
- `TransactionUpdate` — body PUT. Mọi field optional (partial update).
- `TransactionResponse` — DTO 1 transaction.
- `TransactionListMeta` — `{total, page, size}` cho pagination.
- `TransactionListResponse` — `{items, meta}`.

### 7.2.7 `schemas/__init__.py`

Re-export tất cả symbol để code có thể `from app.schemas import TransactionCreate` thay vì path đầy đủ.

## 7.3 `app/models/`

### 7.3.1 `models/entities.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/models/entities.py:1-25
"""Re-export entities từ `pfa_shared.entities` để code API cũ không phải đổi
import path. Nguồn duy nhất ở `backend/shared/pfa_shared/entities.py` (M5)."""
from pfa_shared.entities import (
    Budget,
    Category,
    InsightSnapshot,
    OcrResult,
    ReceiptUpload,
    Transaction,
    User,
    UserMerchantMapping,
)
```

Re-export 8 entity. Mọi router/service vẫn import qua `app.models.entities` để giữ tương thích, nhưng thực tế class sống ở `pfa_shared.entities`.

### 7.3.2 `models/__init__.py`

Re-export lần nữa để `alembic/env.py` có thể `from app.models import *` để load metadata (xem `09-migrations.md`).

## 7.4 `app/repos/`

Thư mục rỗng — placeholder cho repository pattern phase sau. Hiện routers truy cập DB trực tiếp qua `Session`.

## 7.5 `tests/conftest.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/tests/conftest.py:24-52
@pytest.fixture(scope="session")
def engine() -> Engine:
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(autouse=True)
def _reset_database(engine: Engine) -> Generator[None, None, None]:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _override_health_engine(engine, monkeypatch) -> None:
    """Force health_checks.check_database dùng test SQLite engine."""
    monkeypatch.setattr("app.services.health_checks.engine", engine)
```

5 fixture:

1. **`engine`** (session scope): SQLite in-memory + `StaticPool` (share connection giữa thread). Tạo 1 lần cho toàn bộ test session.

2. **`_reset_database`** (autouse): drop + create tables trước mỗi test → isolation.

3. **`_override_health_engine`** (autouse, monkeypatch): force `health_checks.engine` về test engine. Quan trọng vì `health_checks.py` import `engine` ở module-load-time → bound vào Postgres production.

4. **`_reset_storage_singleton`** (autouse): clear `get_storage_service.cache_clear()` để test có thể đổi `storage_backend` setting.

5. **`db_session`**, **`client`** — yield session/TestClient với `app.dependency_overrides`.

6. **`auth_user`**: seed 1 user + tạo JWT + set cookie lên TestClient. Dùng cho mọi router cần auth.

## 7.6 `scripts/seed_categories.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/scripts/seed_categories.py:7-46
DEFAULT_CATEGORIES: tuple[str, ...] = (
    "Food", "Transport", "Shopping", "Bills",
    "Health", "Education", "Entertainment", "Other",
)


def seed_default_categories() -> int:
    created = 0
    with Session(engine) as session:
        for category_name in DEFAULT_CATEGORIES:
            statement = select(Category).where(
                Category.user_id.is_(None),
                Category.name == category_name,
            )
            existing = session.exec(statement).first()
            if existing is not None:
                continue
            session.add(Category(user_id=None, name=category_name, is_system=True))
            created += 1
        session.commit()
    return created


if __name__ == "__main__":
    total = seed_default_categories()
    print(f"Seeded {total} default categories.")
```

CLI script chạy sau khi `alembic upgrade head` để insert 8 system categories. Idempotent — chạy lại không tạo duplicate.
