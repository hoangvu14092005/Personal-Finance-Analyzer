# 5. Phân tích chi tiết — `backend/api/app/api/*` (Routers)

> Mỗi router tương ứng 1 resource HTTP. Convention: prefix tự định nghĩa trong file, mount vào `app` ở `main.py` với `settings.api_v1_prefix` (`/api/v1`).

## 5.1 `app/api/health.py`

3 endpoint:

| Endpoint | Hàm | Status code |
|---|---|---|
| `GET /health` | `health_check` | 200 |
| `GET /health/live` | `health_live` | 200 |
| `GET /health/ready` | `health_ready` | 200/503 |

### `health_check() -> HealthResponse`

Liveness — backwards-compat với endpoint cũ. Trả `HealthResponse(service=ServiceName.API)`. Không phụ thuộc DB/Redis/S3 → dùng cho K8s liveness probe (đảm bảo process còn alive).

### `health_live() -> HealthResponse`

Alias rõ nghĩa cho `/health`. Cùng response.

### `health_ready(response: Response) -> ReadinessResponse`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/api/health.py:43-70
async def health_ready(response: Response) -> ReadinessResponse:
    settings = get_settings()
    results = await run_readiness_checks(settings)
    components = [
        ComponentStatus(
            name=result.name,
            status="ok" if result.ok else "down",
            error=result.error,
        )
        for result in results
    ]
    overall_ok = all(result.ok for result in results)
    if not overall_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ok" if overall_ok else "degraded",
        components=components,
    )
```

Deep readiness — gọi `run_readiness_checks(settings)` để ping DB + Redis + S3 (xem `services/health_checks.py`). 

**Quy ước**:
- 200 OK: tất cả components ok → app sẵn sàng nhận traffic.
- 503 Service Unavailable: ≥ 1 component down → LB nên loại pod khỏi rotation.
- Body luôn `ReadinessResponse` (kể cả 503) → monitoring biết component nào fail.

## 5.2 `app/api/v1/auth.py`

5 hàm/endpoint, prefix `/auth`:

### `to_profile_response(user: User) -> ProfileResponse`

Helper convert ORM → DTO. Raise `ValueError` nếu `user.id is None` (defensive — không xảy ra sau commit).

### `POST /auth/register` — `register()`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/api/v1/auth.py:30-54
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    session: Session = Depends(get_session),
) -> AuthResponse:
    existing_user = session.exec(select(User).where(User.email == payload.email)).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        currency=payload.currency,
        timezone=payload.timezone,
        locale=payload.locale,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return AuthResponse(user=to_profile_response(user))
```

Pipeline:
1. Check email duplicate → 409 (chống register lặp).
2. `hash_password` (argon2) → insert.
3. Trả `AuthResponse(user=ProfileResponse)` 201. **Không** set cookie ở đây — user phải login riêng sau register.

### `POST /auth/login` — `login()`

Pipeline:
1. Find user by email.
2. `verify_password` — fail thì raise 401 với message `Invalid email or password` (chống user enumeration: email tồn tại / không tồn tại trả cùng message).
3. `create_access_token` → `set_auth_cookie`.
4. Trả profile.

### `POST /auth/logout` — `logout()`

`clear_auth_cookie` + 204 No Content.

### `GET /auth/me` — `get_me()`

Trả profile của `current_user` từ `Depends(get_current_user)`.

## 5.3 `app/api/v1/categories.py`

1 endpoint duy nhất `GET /api/v1/categories`. Prefix `/categories`.

### Helper `_to_response(category: Category) -> CategoryResponse`

Raise 500 nếu `id is None`.

### `GET /categories` — `list_categories()`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/api/v1/categories.py:40-63
@router.get("", response_model=CategoryListResponse)
def list_categories(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CategoryListResponse:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Invalid user")

    statement = (
        select(Category)
        .where(
            or_(
                col(Category.is_system).is_(True),
                Category.user_id == current_user.id,
            ),
        )
        .order_by(col(Category.is_system).desc(), col(Category.name).asc())
    )
    rows = session.exec(statement).all()
    return CategoryListResponse(items=[_to_response(row) for row in rows])
```

Query SQLModel với `OR(is_system=True, user_id=current_user.id)`, sort `is_system DESC, name ASC` → system categories luôn lên đầu để UI render default options đầu tiên. Trả `CategoryListResponse(items=[...])`.

## 5.4 `app/api/v1/dashboard.py`

1 endpoint `GET /api/v1/dashboard/summary`. Prefix `/dashboard`.

**Hằng cap**: `MAX_TOP_CATEGORIES_LIMIT = 20`, `MAX_RECENT_TRANSACTIONS_LIMIT = 50` — chống client request quá nặng.

### Helper `_build_range_info(range_, preset) -> RangeInfo`

Convert `DateRange` + `RangePreset` thành DTO có sẵn `.days`.

### `GET /dashboard/summary` — `get_dashboard_summary()`

Pipeline 6 bước:

1. **Validate user**: `current_user.id is None` → 401.
2. **Parse preset**: `RangePreset(range)` raise `ValueError` → 400 với danh sách preset cho phép.
3. **Resolve current range**: `resolve_range(preset, start_date, end_date)`. `InvalidDateRangeError` → 400 (custom thiếu start/end, start > end, hoặc days > 366).
4. **Tính previous range**: `previous_period(current, preset)`.
5. **Compute summary**: `compute_summary(...)` từ `services/analytics.py` — 4 query.
6. **Map sang response**: convert dataclass → Pydantic `DashboardSummaryResponse`.

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/api/v1/dashboard.py:140-176
return DashboardSummaryResponse(
    range=_build_range_info(current_range, preset),
    previous_range=_build_range_info(previous_range, preset),
    current=PeriodTotalsResponse(
        total_spend=summary.current.total_spend,
        transaction_count=summary.current.transaction_count,
    ),
    previous=PeriodTotalsResponse(...),
    delta_amount=summary.delta_amount,
    delta_percent=summary.delta_percent,
    top_categories=[
        CategoryBreakdownResponse(
            category_id=cat.category_id,
            name=cat.name,
            color=cat.color,
            total_amount=cat.total_amount,
            transaction_count=cat.transaction_count,
            percentage=cat.percentage,
        )
        for cat in summary.top_categories
    ],
    recent_transactions=[
        RecentTransactionResponse(
            id=tx.id,
            merchant_name=tx.merchant_name,
            amount=tx.amount,
            currency=tx.currency,
            transaction_date=date.fromisoformat(tx.transaction_date),
            ...
        )
        for tx in summary.recent_transactions
    ],
)
```

Lưu ý: `tx.transaction_date` trong dataclass là string ISO (do `_query_recent_transactions` dùng `.isoformat()`); ở đây convert ngược lại `date.fromisoformat(...)` cho Pydantic validate.

## 5.5 `app/api/v1/receipts.py`

4 endpoint + 1 helper. Prefix `/receipts`.

### Helper `_ensure_receipt_owner(session, receipt_id, user_id) -> ReceiptUpload`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/api/v1/receipts.py:28-36
def _ensure_receipt_owner(
    session: Session,
    receipt_id: int,
    user_id: int,
) -> ReceiptUpload:
    receipt = session.get(ReceiptUpload, receipt_id)
    if receipt is None or receipt.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    return receipt
```

Trả 404 (không phải 403) cho cả 2 case: receipt không tồn tại + receipt thuộc user khác → chống enumeration ID.

### `POST /receipts/upload` — `upload_receipt()`

Hàm phức tạp nhất. Pipeline:

1. **Auth check** → 401 nếu `user.id is None`.
2. **Read body** → `await file.read()`.
3. **Validate** → `validate_upload_file(file, len(file_content), settings.ocr_max_file_size_mb)`.
4. **Generate storage key** → `f"{user_id}/{uuid4().hex}{ext}"` (namespace per user, UUID tránh collision).
5. **Upload bytes** → `storage.upload_bytes(...)` → `StoredObject`.
6. **Insert ReceiptUpload với status PROCESSING** (set TRƯỚC khi enqueue):

   ```python
   receipt = ReceiptUpload(
       user_id=current_user.id,
       file_name=file.filename or generated_name,
       content_type=file.content_type or "application/octet-stream",
       file_size_bytes=stored_object.size_bytes,
       storage_key=stored_object.storage_key,
       status=ReceiptStatus.PROCESSING.value,
   )
   ```

7. **Enqueue OCR job** → `await enqueue_ocr_job(receipt.id)`.
8. **Rollback nếu enqueue fail**:

   ```python
   if not enqueued:
       receipt.status = ReceiptStatus.UPLOADED.value
       receipt.error_code = "queue_unavailable"
       receipt.error_message = "OCR queue is not available. You can retry later."
       session.add(receipt); session.commit(); session.refresh(receipt)
   ```

9. **Trả response** với `receipt_id + status` (frontend poll dựa trên status này).

**Lý do set `PROCESSING` TRƯỚC khi enqueue** (từ comment code):

> Nếu set sau, worker có thể finish (READY) trước khi API kịp ghi PROCESSING → API sẽ ghi đè READY thành PROCESSING → frontend mãi thấy processing dù đã xong.

**Lý do enqueue fail KHÔNG chuyển sang FAILED** (từ comment code):

> Lỗi nằm ở queue, không phải OCR engine → để FAILED sẽ misleading. Dùng `error_code=queue_unavailable` để frontend hiểu user có thể retry hoặc fallback manual entry.

### `GET /receipts/{id}` — `get_receipt_status()`

`_ensure_receipt_owner` → trả `ReceiptStatusResponse(receipt_id, file_name, content_type, status, error_code, error_message, created_at)`. Frontend poll endpoint này để biết khi nào OCR done.

### `GET /receipts/{id}/ocr-result` — `get_receipt_ocr_result()`

`_ensure_receipt_owner` → query `OcrResult WHERE receipt_upload_id = ?`. 404 nếu OCR chưa xong. Trả raw OCR data (`raw_text`, `confidence`, `normalized_payload` JSON string).

### `GET /receipts/{id}/draft` — `get_receipt_draft()`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/api/v1/receipts.py:143-182
@router.get("/{receipt_id}/draft", response_model=DraftReviewResponse)
def get_receipt_draft(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DraftReviewResponse:
    if current_user.id is None: raise 401
    receipt = _ensure_receipt_owner(session, receipt_id, current_user.id)
    ocr_result = session.exec(
        select(OcrResult).where(OcrResult.receipt_upload_id == receipt_id),
    ).first()
    if ocr_result is None: raise 404 "OCR result not ready"

    draft = build_draft_review(
        session=session,
        receipt=receipt,
        ocr_result=ocr_result,
        user_id=current_user.id,
    )

    return DraftReviewResponse(
        receipt_id=draft.receipt_id,
        receipt_status=draft.receipt_status,
        provider=draft.provider,
        confidence=draft.confidence,
        merchant_name=draft.merchant_name,
        transaction_date=draft.transaction_date,
        amount=draft.amount,
        currency=draft.currency,
        suggested_category_id=draft.suggested_category_id,
        raw_text=draft.raw_text,
    )
```

Endpoint chuẩn cho UI review form. Gộp `ReceiptUpload + OcrResult` qua `build_draft_review` (parse JSON, suggest category từ user mapping).

## 5.6 `app/api/v1/transactions.py`

4 endpoint + 4 helper — router phức tạp nhất. Prefix `/transactions`.

**Hằng**: `DEFAULT_PAGE_SIZE = 20`, `MAX_PAGE_SIZE = 100`.

### Helpers

#### `_to_response(transaction: Transaction) -> TransactionResponse`

Map ORM → DTO. Raise 500 nếu `id is None`.

#### `_ensure_receipt_owner(session, receipt_id, user_id) -> ReceiptUpload`

Tương tự `receipts.py`.

#### `_ensure_transaction_owner(session, transaction_id, user_id) -> Transaction`

```python
def _ensure_transaction_owner(session, transaction_id, user_id) -> Transaction:
    transaction = session.get(Transaction, transaction_id)
    if transaction is None or transaction.user_id != user_id:
        raise HTTPException(404, "Transaction not found")
    return transaction
```

#### `_ensure_category_accessible(session, category_id, user_id) -> Category`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/api/v1/transactions.py:86-105
def _ensure_category_accessible(
    session: Session,
    category_id: int,
    user_id: int,
) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    is_owned = category.user_id == user_id
    if not category.is_system and not is_owned:
        raise HTTPException(status_code=404, detail="Category not found")

    return category
```

Category phải `is_system=True` HOẶC `user_id == current_user.id`. Trả 404 cả khi chỉ là access denied → chống enumeration.

### `POST /transactions` — `create_transaction()`

Pipeline:

1. **Auth** + ownership receipt (nếu có `receipt_upload_id`).
2. **Resolve `category_id`**:
   - User truyền → validate accessible.
   - User không truyền → gọi `suggest_category_for_merchant(...)` từ mapping học được. Có thể trả `None` (transaction không gán category).
3. **Insert Transaction**.
4. **Học mapping** nếu user truyền **cả** `merchant_name + category_id`:

   ```python
   if (payload.merchant_name and payload.category_id is not None):
       remember_user_merchant_category(
           session=session,
           user_id=current_user.id,
           merchant_name=payload.merchant_name,
           category_id=payload.category_id,
       )
   ```

   → Lần upload sau có cùng merchant sẽ suggest đúng category.

### `GET /transactions` — `list_transactions()`

Filter + pagination:

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/api/v1/transactions.py:165-215
def list_transactions(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    category_id: int | None = Query(default=None, gt=0),
    merchant: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> TransactionListResponse:
    if current_user.id is None: raise 401

    if start_date and end_date and start_date > end_date:
        raise HTTPException(400, "start_date must be on or before end_date")

    base_query = select(Transaction).where(Transaction.user_id == current_user.id)
    if start_date is not None: base_query = base_query.where(Transaction.transaction_date >= start_date)
    if end_date is not None: base_query = base_query.where(Transaction.transaction_date <= end_date)
    if category_id is not None: base_query = base_query.where(Transaction.category_id == category_id)
    if merchant:
        like_pattern = f"%{merchant.strip()}%"
        base_query = base_query.where(col(Transaction.merchant_name).ilike(like_pattern))

    count_query = select(func.count()).select_from(base_query.subquery())
    total = session.exec(count_query).one()

    paged_query = (
        base_query.order_by(
            col(Transaction.transaction_date).desc(),
            col(Transaction.id).desc(),
        )
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = session.exec(paged_query).all()

    return TransactionListResponse(
        items=[_to_response(row) for row in rows],
        meta=TransactionListMeta(total=int(total), page=page, size=size),
    )
```

Đặc điểm:
- Filter optional: `start_date`, `end_date`, `category_id`, `merchant` (LIKE `%...%`).
- Validate `start_date <= end_date` → 400.
- 2 query: COUNT cho total, SELECT cho items (offset/limit).
- Sort `transaction_date DESC, id DESC` để 2 transaction cùng ngày deterministic.

### `PUT /transactions/{id}` — `update_transaction()`

Partial update:

1. Ownership check.
2. `payload.model_dump(exclude_unset=True)` → chỉ field user gửi.
3. Empty body → return state hiện tại (idempotent — request không thay đổi gì vẫn return 200).
4. Nếu update `category_id != None` → validate accessible.
5. `setattr` từng field → commit.
6. Re-learn mapping nếu `merchant_name` hoặc `category_id` được động VÀ cả 2 đều non-null.

### `DELETE /transactions/{id}` — `delete_transaction()`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/api/v1/transactions.py:275-296
@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    if current_user.id is None: raise 401
    transaction = _ensure_transaction_owner(session, transaction_id, current_user.id)
    session.delete(transaction)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Hard delete (comment ghi rõ MVP chưa có audit trail / soft-delete). Dashboard summary tự cập nhật vì chỉ aggregate từ rows hiện tại.
