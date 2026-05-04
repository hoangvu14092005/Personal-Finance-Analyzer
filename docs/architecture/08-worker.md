# 8. Phân tích chi tiết — `backend/worker`

> Worker là TaskIQ consumer process. Lifecycle: chạy `taskiq worker --app-dir worker worker_app:broker` → broker BLPOP từ Redis → invoke task handler → commit DB.

## 8.1 Cấu trúc & dependencies

```
backend/worker/
├── worker_app.py        # broker init + settings
├── tasks.py             # ⭐ ping_task + process_ocr_job + run_ocr_for_receipt
├── ocr_provider.py      # Protocol OCRProvider + MockOCRProvider
├── run_ping.py          # Manual dispatch ping_task để smoke test
└── tests/               # 3 test file
```

`pyproject.toml` declare 6 dependency:

```toml
dependencies = [
  "boto3>=1.35.0,<2.0.0",
  "personal-finance-analyzer-shared",
  "psycopg[binary]>=3.2.0,<4.0.0",
  "sqlmodel>=0.0.22,<1.0.0",
  "taskiq>=0.11.0,<1.0.0",
  "taskiq-redis>=1.0.0,<2.0.0",
]
```

Worker **không** cần `fastapi`, `pwdlib`, `pyjwt` — chỉ libs xử lý DB + storage + queue.

## 8.2 `worker/worker_app.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/worker/worker_app.py:1-13
from pfa_shared.config import CommonSettings
from pfa_shared.logging import get_logger
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

settings = CommonSettings.from_env()
logger = get_logger("worker", level=settings.log_level)
logger.info("Initializing worker broker")

broker = ListQueueBroker(url=settings.redis_url).with_result_backend(
    RedisAsyncResultBackend(redis_url=settings.redis_url),
)
```

3 module-level singleton:
- `settings`: load từ env (cùng `CommonSettings.from_env()` với API → đảm bảo cùng `redis_url`).
- `logger`: dùng `pfa_shared.logging.get_logger` (lightweight).
- `broker`: `ListQueueBroker` (Redis LIST) + `RedisAsyncResultBackend` (lưu result để query qua `wait_result`).

Tại sao cùng `redis_url` quan trọng? API enqueue qua `tasks:process_ocr_job`, worker phải BLPOP cùng key list trên cùng Redis instance.

## 8.3 `worker/ocr_provider.py`

> M5 refactor: từ `extract_text(file_path: Path)` (bind chặt local FS) sang `extract_text(content: bytes, source_hint: str)` (provider chỉ thấy bytes, worker dùng storage adapter download).

### Dataclass

```python
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
```

### Protocol `OCRProvider`

```python
class OCRProvider(Protocol):
    def extract_text(self, content: bytes, source_hint: str = "") -> OCRRawResult: ...
    def normalize_receipt(self, raw: OCRRawResult) -> OCRNormalizedReceipt: ...
```

`source_hint` là filename hoặc storage_key gốc — chỉ dùng cho mock log/debug, không phải để mở file.

### `MockOCRProvider`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/worker/ocr_provider.py:41-58
class MockOCRProvider:
    def extract_text(self, content: bytes, source_hint: str = "") -> OCRRawResult:
        # Mock: dùng source_hint làm tên file giả trong raw_text.
        # `content` không được parse — chỉ lưu kích thước để verify đã đọc bytes.
        label = source_hint or f"<{len(content)} bytes>"
        return OCRRawResult(
            provider="mock",
            raw_text=f"Receipt text extracted from {label}",
            confidence=0.92,
        )

    def normalize_receipt(self, raw: OCRRawResult) -> OCRNormalizedReceipt:
        return OCRNormalizedReceipt(
            merchant="Mock Mart",
            transaction_date="2026-03-30",
            total_amount=Decimal("125000.00"),
            currency="VND",
        )
```

### `get_ocr_provider() -> OCRProvider`

Hiện trả `MockOCRProvider()` cố định. Khi mở provider thật, sửa hàm này (hoặc dùng registry pattern như API).

## 8.4 `worker/tasks.py` — File quan trọng nhất

3 phần: 2 task TaskIQ + 1 hàm core logic.

### `build_ping_response() -> str` + `ping_task()`

```python
def build_ping_response() -> str:
    return "ping"


@broker.task
async def ping_task() -> str:
    return build_ping_response()
```

Smoke test task. Tách `build_ping_response` để test unit (`test_ping_task.py` không cần broker).

### `run_ocr_for_receipt(session, storage, provider, receipt_id) -> str` — Core logic

> Tách core logic khỏi TaskIQ task để testable với SQLite + LocalStorage, không cần Redis/Postgres.

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/worker/tasks.py:37-120
def run_ocr_for_receipt(
    session: Session,
    storage: StorageService,
    provider: OCRProvider,
    receipt_id: int,
) -> str:
    """Core logic của OCR job — testable không cần Redis/TaskIQ.

    Returns one of: "missing_receipt", "ready", "failed".
    """
    receipt = session.get(ReceiptUpload, receipt_id)
    if receipt is None:
        return "missing_receipt"

    # Bước 1: đánh dấu PROCESSING (idempotent — chạy lại task không sao).
    receipt.status = ReceiptStatus.PROCESSING.value
    receipt.error_code = None
    receipt.error_message = None
    session.add(receipt); session.commit()

    try:
        # Bước 2: tải bytes từ storage (local FS hoặc S3).
        try:
            content = storage.download_bytes(receipt.storage_key)
        except StorageNotFoundError as exc:
            raise RuntimeError(f"storage_key missing: {receipt.storage_key}") from exc

        # Bước 3: gọi OCR provider.
        raw_result = provider.extract_text(content, source_hint=receipt.storage_key)
        normalized = provider.normalize_receipt(raw_result)

        payload = {
            "merchant": normalized.merchant,
            "transaction_date": normalized.transaction_date,
            "total_amount": str(normalized.total_amount),
            "currency": normalized.currency,
        }

        # Bước 4: upsert OcrResult.
        existing = session.exec(
            select(OcrResult).where(OcrResult.receipt_upload_id == receipt_id),
        ).first()
        now = datetime.now(tz=UTC)

        if existing is None:
            session.add(
                OcrResult(
                    receipt_upload_id=receipt_id,
                    provider=raw_result.provider,
                    raw_text=raw_result.raw_text,
                    confidence=raw_result.confidence,
                    normalized_payload=json.dumps(payload),
                    status=ReceiptStatus.READY.value,
                    created_at=now,
                ),
            )
        else:
            existing.provider = raw_result.provider
            existing.raw_text = raw_result.raw_text
            existing.confidence = raw_result.confidence
            existing.normalized_payload = json.dumps(payload)
            existing.status = ReceiptStatus.READY.value
            session.add(existing)

        # Bước 5: đánh dấu receipt READY.
        receipt.status = ReceiptStatus.READY.value
        receipt.error_code = None
        receipt.error_message = None
        session.add(receipt); session.commit()
        return "ready"

    except Exception as exc:
        # Rollback bất kỳ pending change → ghi lại receipt với status FAILED.
        session.rollback()
        receipt = session.get(ReceiptUpload, receipt_id)
        if receipt is not None:
            receipt.status = ReceiptStatus.FAILED.value
            receipt.error_code = "ocr_failed"
            receipt.error_message = str(exc)[:500]
            session.add(receipt); session.commit()
        return "failed"
```

**Pipeline 5 bước**:

1. **Lookup receipt**: missing → return sentinel `"missing_receipt"`. Có thể xảy ra nếu user xóa receipt trong lúc job đang queue.

2. **Mark PROCESSING**: idempotent — chạy lại task vẫn ok. Reset `error_code/error_message` để clear state retry.

3. **Download bytes**: `storage.download_bytes` qua adapter (local hoặc S3). `StorageNotFoundError` → re-raise as `RuntimeError` với message rõ ràng để fall vào except branch.

4. **OCR**: `extract_text` → `OCRRawResult`; `normalize_receipt` → `OCRNormalizedReceipt`. Payload JSON normalize chuẩn để frontend parse.

5. **UPSERT OcrResult + mark READY**:
   - `OcrResult.receipt_upload_id UNIQUE` → 1 receipt có nhiều nhất 1 OcrResult.
   - Lần đầu: INSERT.
   - Retry: UPDATE existing (idempotent).
   - Cuối cùng `receipt.status = READY` để frontend poll thấy done.

**Failure path**:
- Catch mọi exception (storage missing, OCR provider raise, DB constraint...).
- `session.rollback()` để revert pending changes (vd. status PROCESSING đã commit thì giữ nguyên, nhưng pending OcrResult chưa commit thì revert).
- Re-fetch receipt (sau rollback session detach), set `FAILED + error_code='ocr_failed' + error_message`. Truncate 500 chars để chống storage flood.
- Return `"failed"` → TaskIQ log + caller (`process_ocr_job`) propagate.

### `process_ocr_job(receipt_id: int) -> str` — TaskIQ entry

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/worker/tasks.py:123-133
@broker.task
async def process_ocr_job(receipt_id: int) -> str:
    """TaskIQ entry point. Tạo engine + session + storage cho mỗi job (worker
    là long-lived; engine pooled qua sqlmodel). Body delegate sang
    `run_ocr_for_receipt` để dễ unit test."""
    engine = create_engine(settings.database_url)
    storage = build_storage_service(settings)
    provider = get_ocr_provider()

    with Session(engine) as session:
        return run_ocr_for_receipt(session, storage, provider, receipt_id)
```

3 wiring:
- `engine = create_engine(...)` — TÁI tạo mỗi job (comment ghi "worker là long-lived; engine pooled qua sqlmodel"). Có thể optimize sau bằng module-level engine.
- `storage = build_storage_service(settings)` — tạo mới mỗi job (chấp nhận overhead trong MVP).
- `provider = get_ocr_provider()` — tạo mới.

Body delegate `run_ocr_for_receipt(...)` để unit test dễ (test mock 3 dependency).

### Task name discovery

TaskIQ default task name = `f"{module_name}:{func_name}"`. File `tasks.py` ở `app-dir worker` → module name `tasks` → task name `tasks:process_ocr_job`. Name này phải KHỚP với hằng `OCR_TASK_NAME` ở `api/app/services/ocr_queue.py`.

## 8.5 `worker/run_ping.py` — Manual smoke test

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/worker/run_ping.py:1-17
import asyncio

from tasks import ping_task


async def main() -> None:
    task = await ping_task.kiq()
    result = await task.wait_result(timeout=5)
    if result.is_err:
        raise RuntimeError(f"ping_task failed: {result.error}")
    print(result.return_value)


if __name__ == "__main__":
    asyncio.run(main())
```

Chạy ở terminal thứ 2 (terminal 1 đang chạy `taskiq worker`):
1. `ping_task.kiq()` enqueue task.
2. `wait_result(timeout=5)` block tới khi worker xử lý xong + ghi result vào `RedisAsyncResultBackend`.
3. Print `"ping"`.

Mục đích: verify Redis + worker process hoạt động trước khi test pipeline OCR thật.

## 8.6 `worker/tests/test_run_ocr_for_receipt.py`

Integration test cho core logic, KHÔNG cần Redis/MinIO/Postgres.

### Fixtures

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/worker/tests/test_run_ocr_for_receipt.py:27-40
@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorageService:
    return LocalStorageService(root_dir=tmp_path)
```

SQLite in-memory + `LocalStorageService` qua `tmp_path` (auto cleanup sau test).

### Test cases (4)

1. **`test_happy_path_creates_ocr_result_and_marks_ready`**:
   - Seed user + upload bytes vào storage + tạo `ReceiptUpload(status=UPLOADED)`.
   - Run `run_ocr_for_receipt(...)` → return `"ready"`.
   - Assert `receipt.status == READY`, `error_code is None`.
   - Assert `OcrResult` được tạo với `provider="mock"` và payload JSON chứa "Mock Mart".

2. **`test_rerun_is_idempotent_no_duplicate_ocr_results`**:
   - Run 2 lần liên tiếp.
   - Assert chỉ 1 row `OcrResult` (UPSERT đúng).

3. **`test_storage_missing_marks_receipt_failed`**:
   - Seed receipt nhưng KHÔNG upload bytes.
   - Run → return `"failed"`.
   - Assert `receipt.status == FAILED`, `error_code == "ocr_failed"`, `error_message` chứa storage_key.

4. **`test_missing_receipt_returns_sentinel`**:
   - Run với `receipt_id=9999` (không tồn tại) → return `"missing_receipt"`.

Coverage 4 nhánh chính của `run_ocr_for_receipt`.
