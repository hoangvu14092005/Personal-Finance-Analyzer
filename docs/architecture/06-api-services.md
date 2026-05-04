# 6. Phân tích chi tiết — `backend/api/app/services/*`

> Service layer chứa business logic thuần — không biết HTTP. Mỗi service nhận `Session` (hoặc settings) và trả dataclass/`None`. Routers chịu trách nhiệm map dataclass sang Pydantic response.

## 6.1 `services/password_service.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/password_service.py:1-13
from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()


def hash_password(raw_password: str) -> str:
    return _password_hash.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    return _password_hash.verify(raw_password, password_hash)
```

`pwdlib.PasswordHash.recommended()` → argon2 default. Wrap để dễ thay backend (vd. bcrypt) sau này. `_password_hash` module-level singleton để khởi tạo 1 lần.

**Hàm**:
- `hash_password(raw_password) -> str`: trả hash PHC string (`$argon2id$v=19$m=...`).
- `verify_password(raw_password, password_hash) -> bool`: constant-time compare; không raise nếu hash invalid → trả `False`.

## 6.2 `services/receipt_validation.py`

3 hằng + 1 hàm:

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/receipt_validation.py:7-38
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}


def validate_upload_file(
    upload_file: UploadFile,
    file_size_bytes: int,
    max_file_size_mb: int,
) -> None:
    extension = Path(upload_file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported file extension. Allowed: JPG, PNG, PDF.")

    if upload_file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, "Unsupported MIME type. ...")

    max_bytes = max_file_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise HTTPException(400, f"File too large. Max size is {max_file_size_mb}MB.")
```

**Defense in depth — 3 check**:
1. Extension whitelist (lowercase).
2. MIME whitelist (client-supplied; spoofable nhưng vẫn lọc bớt 80% case).
3. Size cap (server-side, không tin client `Content-Length`).

## 6.3 `services/category_suggestion.py`

3 hàm baseline (Phase 3.3):

### `normalize_merchant_name(value: str) -> str`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/category_suggestion.py:18-20
def normalize_merchant_name(value: str) -> str:
    """Chuan hoa ten merchant de tra cuu mapping deterministic."""
    return normalize_whitespace(value).casefold()
```

`normalize_whitespace` (gộp khoảng trắng dư) + `casefold` (lower-case Unicode-aware) để "Mock Mart" và "mock  mart" cùng key.

### `suggest_category_for_merchant(session, user_id, merchant_name) -> int | None`

```python
def suggest_category_for_merchant(session, user_id, merchant_name) -> int | None:
    if not merchant_name: return None
    normalized = normalize_merchant_name(merchant_name)
    if not normalized: return None

    mapping = session.exec(
        select(UserMerchantMapping).where(
            UserMerchantMapping.user_id == user_id,
            UserMerchantMapping.normalized_merchant_name == normalized,
        ),
    ).first()

    if mapping is None or mapping.category_id is None: return None
    return mapping.category_id
```

Pipeline:
1. Empty/whitespace input → `None`.
2. Lookup `UserMerchantMapping(user_id, normalized_merchant_name)`.
3. Mapping không tồn tại HOẶC `category_id IS NULL` → `None`.

Caller (`create_transaction`) fallback transaction không có category nếu trả `None`.

### `remember_user_merchant_category(session, user_id, merchant_name, category_id) -> UserMerchantMapping`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/category_suggestion.py:49-81
def remember_user_merchant_category(session, user_id, merchant_name, category_id) -> UserMerchantMapping:
    normalized = normalize_merchant_name(merchant_name)
    existing = session.exec(
        select(UserMerchantMapping).where(
            UserMerchantMapping.user_id == user_id,
            UserMerchantMapping.normalized_merchant_name == normalized,
        ),
    ).first()

    if existing is None:
        mapping = UserMerchantMapping(
            user_id=user_id,
            raw_merchant_name=merchant_name,
            normalized_merchant_name=normalized,
            category_id=category_id,
        )
        session.add(mapping); session.commit(); session.refresh(mapping)
        return mapping

    existing.category_id = category_id
    existing.raw_merchant_name = merchant_name  # update để log raw mới nhất
    session.add(existing); session.commit(); session.refresh(existing)
    return existing
```

UPSERT pattern — nếu chưa có thì insert; có thì update `category_id` và `raw_merchant_name`. Lưu `raw_merchant_name` để debug/UI hiển thị tên gốc user nhập.

## 6.4 `services/draft_review.py`

Gộp `ReceiptUpload + OcrResult` thành `DraftReviewData` (dataclass).

**Schema OCR JSON** (do worker ghi vào `OcrResult.normalized_payload`):

```json
{
  "merchant": "string | null",
  "transaction_date": "ISO date | null",
  "total_amount": "decimal string | null",
  "currency": "string | null"
}
```

### Dataclass `DraftReviewData`

```python
@dataclass(frozen=True)
class DraftReviewData:
    receipt_id: int
    receipt_status: str
    provider: str
    confidence: float | None
    merchant_name: str | None
    transaction_date: date | None
    amount: Decimal | None
    currency: str | None
    suggested_category_id: int | None
    raw_text: str | None
```

### Helper an toàn (defensive parsing)

| Hàm | Input | Output | Catch |
|---|---|---|---|
| `_safe_parse_date(value)` | `object` | `date \| None` | `ValueError` |
| `_safe_parse_decimal(value)` | `object` | `Decimal \| None` | `InvalidOperation, ValueError` |
| `_safe_parse_str(value)` | `object` | `str \| None` (trim, None nếu rỗng) | (type check) |
| `_decode_normalized_payload(raw)` | `str \| None` | `dict[str, object]` (rỗng nếu invalid JSON) | `JSONDecodeError` |

Mọi exception đều log warning (`logger.warning("draft_review.invalid_..."`) chứ không raise — UI vẫn render được form với field thiếu, user tự nhập.

### Hàm chính `build_draft_review(session, receipt, ocr_result, user_id) -> DraftReviewData`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/draft_review.py:92-130
def build_draft_review(session, receipt, ocr_result, user_id) -> DraftReviewData:
    if receipt.id is None:
        raise ValueError("Receipt id must be set before building draft review")

    payload = _decode_normalized_payload(ocr_result.normalized_payload)
    merchant_name = _safe_parse_str(payload.get("merchant"))
    transaction_date = _safe_parse_date(payload.get("transaction_date"))
    amount = _safe_parse_decimal(payload.get("total_amount"))
    currency = _safe_parse_str(payload.get("currency"))
    if currency is not None:
        currency = currency.upper()

    suggested_category_id = suggest_category_for_merchant(
        session, user_id, merchant_name,
    )

    return DraftReviewData(...)
```

5 bước:
1. Defensive `if receipt.id is None`.
2. Parse JSON → dict.
3. Extract 4 field qua helpers.
4. Uppercase `currency` (`vnd` → `VND`).
5. Suggest category qua `suggest_category_for_merchant`.

## 6.5 `services/date_ranges.py`

### Enum `RangePreset` (StrEnum)

| Value | Meaning |
|---|---|
| `7d` | 7 ngày gần nhất tính cả hôm nay |
| `30d` | 30 ngày gần nhất tính cả hôm nay |
| `this_month` | Từ ngày 1 tháng này tới hôm nay (KHÔNG đến cuối tháng) |
| `last_month` | Full tháng trước (1st → ngày cuối tháng đó) |
| `custom` | Yêu cầu `start_date + end_date` từ query |

### Dataclass `DateRange(start, end)`

`@property days = (end - start).days + 1` (inclusive cả 2 đầu).

### Exception `InvalidDateRangeError(ValueError)`

Cho custom range invalid.

### Hằng `MAX_CUSTOM_RANGE_DAYS = 366`

Cap để tránh query quá nặng (1 năm + 1 ngày, chống leap year).

### Helper

#### `_last_day_of_month(year: int, month: int) -> int`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/date_ranges.py:56-64
def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    last_day = next_month_first - timedelta(days=1)
    return last_day.day
```

Tính ngày cuối tháng không cần `calendar` lib (handle leap year đúng).

#### `_previous_month(year: int, month: int) -> tuple[int, int]`

Trả `(year, month)` tháng trước; tháng 1 → tháng 12 năm trước.

### Hàm chính

#### `resolve_range(preset, custom_start, custom_end, today=None) -> DateRange`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/date_ranges.py:73-119
def resolve_range(preset, custom_start, custom_end, today=None) -> DateRange:
    today = today or date.today()

    if preset is RangePreset.LAST_7_DAYS:
        return DateRange(start=today - timedelta(days=6), end=today)

    if preset is RangePreset.LAST_30_DAYS:
        return DateRange(start=today - timedelta(days=29), end=today)

    if preset is RangePreset.THIS_MONTH:
        first_of_month = today.replace(day=1)
        return DateRange(start=first_of_month, end=today)

    if preset is RangePreset.LAST_MONTH:
        prev_year, prev_month = _previous_month(today.year, today.month)
        last_day = _last_day_of_month(prev_year, prev_month)
        return DateRange(
            start=date(prev_year, prev_month, 1),
            end=date(prev_year, prev_month, last_day),
        )

    # CUSTOM
    if custom_start is None or custom_end is None:
        raise InvalidDateRangeError("Custom preset requires both custom_start and custom_end")
    if custom_start > custom_end:
        raise InvalidDateRangeError(f"custom_start ({custom_start}) must be <= custom_end ({custom_end})")
    days = (custom_end - custom_start).days + 1
    if days > MAX_CUSTOM_RANGE_DAYS:
        raise InvalidDateRangeError(f"Custom range cannot exceed {MAX_CUSTOM_RANGE_DAYS} days (got {days})")
    return DateRange(start=custom_start, end=custom_end)
```

`today` parameter chính cho test deterministic (inject `today=date(2026, 6, 15)`).

#### `previous_period(current: DateRange, preset: RangePreset) -> DateRange`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/date_ranges.py:122-149
def previous_period(current: DateRange, preset: RangePreset) -> DateRange:
    if preset is RangePreset.THIS_MONTH:
        prev_year, prev_month = _previous_month(current.start.year, current.start.month)
        last_day = _last_day_of_month(prev_year, prev_month)
        return DateRange(
            start=date(prev_year, prev_month, 1),
            end=date(prev_year, prev_month, last_day),
        )

    if preset is RangePreset.LAST_MONTH:
        # current đang là last month → previous = tháng trước nữa.
        prev_year, prev_month = _previous_month(current.start.year, current.start.month)
        last_day = _last_day_of_month(prev_year, prev_month)
        return DateRange(...)

    # 7d / 30d / custom: rolling window cùng kích thước.
    days = current.days
    end = current.start - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return DateRange(start=start, end=end)
```

Logic:
- `this_month` / `last_month` → tháng trước nữa (full tháng).
- `7d` / `30d` / `custom` → rolling window cùng độ dài N ngày, kết thúc ngay TRƯỚC `current.start` (tránh overlap).

Vd. `current = [2026-06-01, 2026-06-30]` (30d) → `previous = [2026-05-02, 2026-05-31]` (30d).

## 6.6 `services/analytics.py`

Service trọng tâm cho dashboard. 4 dataclass + 4 hàm.

### Dataclass

```python
@dataclass(frozen=True, slots=True)
class CategoryBreakdown:
    category_id: int | None  # None = giao dịch không gán category
    name: str
    color: str | None
    total_amount: Decimal
    transaction_count: int
    percentage: float  # 0..100, làm tròn 2 chữ số

@dataclass(frozen=True, slots=True)
class RecentTransactionItem:
    id: int
    merchant_name: str | None
    amount: Decimal
    currency: str
    transaction_date: str  # ISO format YYYY-MM-DD
    category_id: int | None
    category_name: str | None

@dataclass(frozen=True, slots=True)
class PeriodTotals:
    total_spend: Decimal
    transaction_count: int

@dataclass(frozen=True, slots=True)
class DashboardSummary:
    current: PeriodTotals
    previous: PeriodTotals
    delta_amount: Decimal
    delta_percent: float | None
    top_categories: list[CategoryBreakdown]
    recent_transactions: list[RecentTransactionItem]
```

### Hằng

- `DEFAULT_TOP_CATEGORIES_LIMIT = 5`
- `DEFAULT_RECENT_TRANSACTIONS_LIMIT = 5`

### `_query_period_totals(session, user_id, range_) -> PeriodTotals`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/analytics.py:75-94
def _query_period_totals(session, user_id, range_) -> PeriodTotals:
    statement = (
        select(
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
    )
    row = session.exec(statement).one()
    total_raw, count_raw = row
    total = Decimal(str(total_raw)) if total_raw is not None else Decimal("0")
    return PeriodTotals(total_spend=total, transaction_count=int(count_raw or 0))
```

`SUM(amount) + COUNT(id)` với `coalesce(sum, 0)` (SQLite null-safe). Cast `Decimal(str(...))` để đảm bảo precision.

### `_query_top_categories(session, user_id, range_, total_spend, limit=5) -> list[CategoryBreakdown]`

Pipeline 2 query:

1. **Aggregation**: GROUP BY `category_id`, ORDER BY `SUM DESC`, LIMIT `limit`.

   ```python
   total_expr = func.coalesce(func.sum(Transaction.amount), 0).label("total")
   statement = (
       select(
           Transaction.category_id,
           total_expr,
           func.count(Transaction.id).label("cnt"),
       )
       .where(...)
       .group_by(col(Transaction.category_id))
       .order_by(total_expr.desc())
       .limit(limit)
   )
   ```

2. **Hydrate categories**: `WHERE id IN (top_category_ids)` để có `name + color`.

3. **Build breakdowns**:
   - `category_id IS NULL` → label "Chưa phân loại".
   - `percentage = amount / total_spend * 100`, làm tròn 2 chữ số.
   - `total_spend = 0` → percentage = 0 (avoid divide-by-zero).

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/analytics.py:142-167
if category_id is None:
    name = "Chưa phân loại"
    color = None
else:
    cat = category_map.get(category_id)
    name = cat.name if cat is not None else f"Category #{category_id}"
    color = cat.color if cat is not None else None

if total_spend > 0:
    pct_raw = (amount / total_spend) * Decimal("100")
    percentage = float(round(pct_raw, 2))
else:
    percentage = 0.0
```

### `_query_recent_transactions(session, user_id, range_, limit=5) -> list[RecentTransactionItem]`

`SELECT Transaction LEFT JOIN Category` với ORDER BY `transaction_date DESC, id DESC` (deterministic cho 2 transaction cùng ngày).

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/analytics.py:182-210
statement = (
    select(Transaction, Category)
    .join(Category, col(Transaction.category_id) == Category.id, isouter=True)
    .where(...)
    .order_by(col(Transaction.transaction_date).desc(), col(Transaction.id).desc())
    .limit(limit)
)
items: list[RecentTransactionItem] = []
rows: list[Row[tuple[Transaction, Category | None]]] = list(session.exec(statement).all())
for row in rows:
    transaction, category = row
    if transaction.id is None:
        continue
    items.append(
        RecentTransactionItem(
            id=transaction.id,
            ...
            transaction_date=transaction.transaction_date.isoformat(),
            ...
            category_name=category.name if category is not None else None,
        ),
    )
```

LEFT OUTER JOIN cho phép transaction không có category vẫn hiện (`category=None`).

### `compute_summary(session, user_id, current, previous, *, top_categories_limit, recent_transactions_limit) -> DashboardSummary`

Orchestrator 4 query tuần tự:

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/analytics.py:213-265
def compute_summary(...) -> DashboardSummary:
    current_totals = _query_period_totals(session, user_id, current)
    previous_totals = _query_period_totals(session, user_id, previous)

    delta_amount = current_totals.total_spend - previous_totals.total_spend
    if previous_totals.total_spend > 0:
        delta_pct_raw = (delta_amount / previous_totals.total_spend) * Decimal("100")
        delta_percent: float | None = float(round(delta_pct_raw, 2))
    else:
        delta_percent = None  # UI render "—"

    top_categories = _query_top_categories(session, user_id, current, current_totals.total_spend, limit=...)
    recent_transactions = _query_recent_transactions(session, user_id, current, limit=...)

    return DashboardSummary(...)
```

Comment trong code:

> Dataset MVP nhỏ (<10k rows / user) nên không cần optimize hơn. Khi cần có thể gộp #1 + #3 dùng Window function, hoặc cache layer.

`delta_percent = None` khi `previous = 0` để tránh divide-by-zero — UI render "—" thay vì "infinity%".

## 6.7 `services/ocr_queue.py`

Producer phía API push job vào TaskIQ. 4 hàm + 1 hằng + 1 broker singleton.

### Hằng `OCR_TASK_NAME = "tasks:process_ocr_job"`

**Quan trọng**: phải KHỚP với task name worker đăng ký (TaskIQ default `f"{module_name}:{func_name}"`). Worker decorate `process_ocr_job` trong `tasks.py` → name `tasks:process_ocr_job`.

### `get_ocr_broker() -> AsyncBroker` (`@lru_cache(maxsize=1)`)

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/ocr_queue.py:30-48
@lru_cache(maxsize=1)
def get_ocr_broker() -> AsyncBroker:
    settings = CommonSettings.from_env()
    broker = ListQueueBroker(url=settings.redis_url).with_result_backend(
        RedisAsyncResultBackend(redis_url=settings.redis_url),
    )

    @broker.task(task_name=OCR_TASK_NAME)
    async def _process_ocr_job_proxy(receipt_id: int) -> str:  # noqa: ARG001
        raise NotImplementedError(
            "process_ocr_job is consumed by the worker process, not the API",
        )

    return broker
```

**Pattern proxy task**: API đăng ký task có cùng `task_name` với worker để dùng `broker.find_task(...).kiq(...)`. Body proxy chỉ raise vì execution thực ở worker process. 

Comment giải thích lý do tránh anti-pattern `sys.path.insert` để import code worker:

> KHÔNG còn `sys.path.insert` (anti-pattern import worker code từ API).

### `startup_ocr_broker() -> bool`

```python
async def startup_ocr_broker() -> bool:
    try:
        broker = get_ocr_broker()
        await broker.startup()
    except Exception:
        logger.exception("ocr_queue.startup_failed")
        return False
    logger.info("ocr_queue.startup_ok task=%s", OCR_TASK_NAME)
    return True
```

Gọi từ FastAPI `lifespan`. Catch exception → log + return `False` để app vẫn boot khi Redis down.

### `shutdown_ocr_broker() -> None`

Graceful close — best-effort (catch Exception).

### `enqueue_ocr_job(receipt_id: int) -> bool`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/ocr_queue.py:81-113
async def enqueue_ocr_job(receipt_id: int) -> bool:
    broker = get_ocr_broker()
    task = broker.find_task(OCR_TASK_NAME)
    if task is None:
        logger.error("ocr_queue.task_not_registered ...")
        return False

    try:
        await task.kiq(receipt_id)
    except Exception:
        logger.exception("ocr_queue.enqueue_failed receipt_id=%s task=%s", receipt_id, OCR_TASK_NAME)
        return False

    logger.info("ocr_queue.enqueue_success receipt_id=%s task=%s", receipt_id, OCR_TASK_NAME)
    return True
```

- `broker.find_task(OCR_TASK_NAME).kiq(receipt_id)` — đẩy job vào Redis list.
- Catch exception → log đầy đủ kèm `receipt_id` để truy vết → return `False`.
- Caller (`upload_receipt`) dựa kết quả này để rollback status.

## 6.8 `services/health_checks.py`

3 deep check + 1 orchestrator. Mỗi check trả `CheckResult(name, ok, error)`.

### Hằng + Dataclass

```python
DEFAULT_CHECK_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    ok: bool
    error: str | None = None
```

### `check_database(timeout=2.0) -> CheckResult`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/health_checks.py:39-55
async def check_database(timeout: float = DEFAULT_CHECK_TIMEOUT_SECONDS) -> CheckResult:
    def _ping() -> None:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))

    try:
        await asyncio.wait_for(asyncio.to_thread(_ping), timeout=timeout)
    except TimeoutError:
        return CheckResult(name="database", ok=False, error=f"timeout after {timeout}s")
    except Exception as exc:
        return CheckResult(name="database", ok=False, error=str(exc)[:200])
    return CheckResult(name="database", ok=True)
```

`SELECT 1` qua sync engine wrap trong `asyncio.to_thread` (vì SQLModel sync). `asyncio.wait_for` đảm bảo không hang khi DB unreachable. Truncate error message 200 chars để tránh leak.

### `check_redis(redis_url, timeout=2.0) -> CheckResult`

```python
async def check_redis(redis_url, timeout=2.0) -> CheckResult:
    client: Redis | None = None
    try:
        client = Redis.from_url(redis_url, socket_connect_timeout=timeout)
        ping_awaitable = cast("Awaitable[bool]", client.ping())
        await asyncio.wait_for(ping_awaitable, timeout=timeout)
    except TimeoutError: return CheckResult(name="redis", ok=False, error=f"timeout after {timeout}s")
    except Exception as exc: return CheckResult(name="redis", ok=False, error=str(exc)[:200])
    finally:
        if client is not None:
            try: await client.aclose()
            except Exception: pass
    return CheckResult(name="redis", ok=True)
```

Tạo client mới mỗi check (tránh reuse stale connection). Cleanup `aclose()` ở finally — best effort.

### `check_s3(settings, timeout=2.0) -> CheckResult`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/health_checks.py:83-121
async def check_s3(settings, timeout=2.0) -> CheckResult:
    if settings.storage_backend != "s3":
        return CheckResult(name="storage", ok=True, error=None)

    def _head() -> None:
        import boto3
        from botocore.client import Config

        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            ...
            config=Config(
                connect_timeout=timeout,
                read_timeout=timeout,
                retries={"max_attempts": 1},
            ),
        )
        client.head_bucket(Bucket=settings.s3_bucket_private)

    try:
        await asyncio.wait_for(asyncio.to_thread(_head), timeout=timeout * 2)
    except TimeoutError: return CheckResult(name="storage", ok=False, error=f"timeout after {timeout * 2}s")
    except Exception as exc: return CheckResult(name="storage", ok=False, error=str(exc)[:200])
    return CheckResult(name="storage", ok=True)
```

- **Skip nếu local backend**: trả `ok=True` không thật sự ping (filesystem luôn available).
- **boto3 lazy import**: chỉ khi backend=s3 mới load.
- **Timeout double** (4s) vì `head_bucket` cần connect + verify auth.
- `retries={"max_attempts": 1}` để không retry nội bộ boto3 (mục đích là detect down nhanh, không phải resilience).

### `run_readiness_checks(settings) -> list[CheckResult]`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/services/health_checks.py:124-132
async def run_readiness_checks(settings: Settings) -> list[CheckResult]:
    db_task = asyncio.create_task(check_database())
    redis_task = asyncio.create_task(check_redis(settings.redis_url))
    s3_task = asyncio.create_task(check_s3(settings))

    results = await asyncio.gather(db_task, redis_task, s3_task)
    return list(results)
```

`asyncio.gather` chạy 3 check song song → tổng latency = max của 3 timeout (~4s khi tất cả timeout cùng lúc) chứ không phải sum.

Trả list theo thứ tự cố định để test có thể assert theo index nếu muốn.
