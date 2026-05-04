# 4. Phân tích chi tiết — `backend/api/app/{main, core, middleware, dependencies}`

## 4.1 `app/main.py` — Entry point

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/main.py:18-59
settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan: khởi động OCR broker khi app start, đóng khi shutdown."""
    await startup_ocr_broker()
    try:
        yield
    finally:
        await shutdown_ocr_broker()


app = FastAPI(
    title="Personal Finance Analyzer API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(categories_router, prefix=settings.api_v1_prefix)
app.include_router(receipts_router, prefix=settings.api_v1_prefix)
app.include_router(transactions_router, prefix=settings.api_v1_prefix)
app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
```

**Thứ tự khởi tạo**:
1. `get_settings()` — singleton config (lru_cache).
2. `configure_logging()` — setup format + inject `request_id` factory.
3. `lifespan` — khởi/đóng broker OCR. Quan trọng: nếu Redis down, `startup_ocr_broker` log warning và trả `False`, app vẫn boot.
4. Middleware stack (Starlette áp dụng theo thứ tự ngược): Request → `CORSMiddleware` → `RequestIdMiddleware` → endpoint; Response chiều ngược lại.
5. Mount 6 router: `/health` (không prefix) + 5 router v1 (`/api/v1/...`).

## 4.2 `app/core/config.py`

`Settings` class kế thừa `pydantic_settings.BaseSettings` với 30+ field. Pydantic tự động đọc `.env` và map sang field tương ứng (`SettingsConfigDict(env_file=".env")`).

Field quan trọng:

| Field | Default | Vai trò |
|---|---|---|
| `app_env` | `LOCAL` | Trigger validator production |
| `database_url` | `postgresql+psycopg://pfa:pfa@localhost:5432/pfa` | SQLModel engine |
| `redis_url` | `redis://localhost:6379/0` | TaskIQ broker + result backend |
| `s3_*` | MinIO local default | S3 client config |
| `storage_backend` | `local` | Switch storage adapter |
| `ocr_provider` | `mock` | OCR backend |
| `ocr_max_file_size_mb` | 10 | Validate upload size |
| `jwt_secret` | `DEFAULT_JWT_SECRET` (placeholder) | Validator reject ở staging/prod |
| `jwt_access_expire_minutes` | 30 | Access token lifetime |
| `session_cookie_name` | `pfa_session` | Cookie auth name |
| `session_cookie_secure` | `False` | True ở prod (HTTPS) |
| `session_cookie_samesite` | `lax` | CSRF baseline |
| `cors_origins` | `[localhost:3000, 127.0.0.1:3000]` | CORS whitelist |
| `request_id_header` | `X-Request-ID` | Header trace ID |

**3 hàm/validator nổi bật**:

### `parse_cors_origins(value: object) -> list[str]`

`@field_validator("cors_origins", mode="before")` — chạy TRƯỚC khi Pydantic gán giá trị. Hỗ trợ 3 input format:
- comma-separated string từ `.env` (`"a,b,c"` → split + strip),
- list literal (`["a","b"]`) — ép str + strip,
- fallback default cho local nếu input không hợp lệ.

Nhờ vậy `.env` chỉ cần `CORS_ORIGINS=http://localhost:3000,http://localhost:4000` mà không cần JSON syntax.

### `_enforce_production_secrets(self) -> Settings`

`@model_validator(mode="after")` — fail-fast khi `app_env in {STAGING, PROD}`:

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/core/config.py:84-112
@model_validator(mode="after")
def _enforce_production_secrets(self) -> Settings:
    if self.app_env in {AppEnv.STAGING, AppEnv.PROD}:
        if self.jwt_secret == DEFAULT_JWT_SECRET:
            raise ValueError(...)
        if len(self.jwt_secret) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(...)
        if self.storage_backend != "s3":
            raise ValueError(...)
    return self
```

3 invariant production:
- `jwt_secret` ≠ default placeholder.
- `len(jwt_secret) ≥ 32` ký tự.
- `storage_backend == "s3"` (không cho local FS).

Local/test vẫn cho phép default để dev khỏi phải set env.

### `get_settings() -> Settings`

`@lru_cache(maxsize=1)` singleton accessor. Mọi nơi trong code import qua đây để giữ cùng instance.

## 4.3 `app/core/database.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/core/database.py:1-19
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, echo=False)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
```

- `engine`: module-level singleton, pool mặc định của SQLAlchemy.
- **`get_session() -> Generator[Session, None, None]`**: dependency cho FastAPI (`Depends(get_session)`). Yield session, đảm bảo close ở context manager.
- **`create_db_and_tables() -> None`**: dùng cho test/setup ban đầu (production dùng Alembic).

## 4.4 `app/core/logging.py`

3 phần chính:

### `_set_log_record_factory()` (private, idempotent)

Tùy chỉnh `logging.LogRecord` factory để mọi record tự động có attribute `request_id` lấy từ `ContextVar` (set bởi `RequestIdMiddleware`). Dùng module global `_LOG_RECORD_FACTORY_SET` để chỉ setup 1 lần.

Cơ chế:
1. Lưu factory cũ (`old_factory = logging.getLogRecordFactory()`).
2. Tạo factory mới wrap factory cũ + inject `request_id`.
3. `logging.setLogRecordFactory(factory)`.

### `configure_logging()` (public, gọi 1 lần ở `main.py`)

```python
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s",
)
```

Format chuẩn cho mọi service: timestamp + level + logger name + request_id + message.

### `get_logger(name: str) -> Logger`

Factory tiện lợi (proxy `logging.getLogger`). Quy ước naming: `api.{domain}` (vd. `api.request`, `api.ocr_queue`, `api.health_checks`).

## 4.5 `app/core/security.py`

Mọi thứ liên quan JWT cookie. 4 hàm:

### `create_access_token(user_id: int, email: str) -> str`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/core/security.py:14-25
def create_access_token(user_id: int, email: str) -> str:
    settings = get_settings()
    now = datetime.now(tz=UTC)
    expires_at = now + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
```

HS256, payload chuẩn `{sub, email, iat, exp, type}`. `sub` là str(user_id) theo JWT spec.

### `verify_access_token(token: str) -> dict[str, Any]`

`jwt.decode` raise `InvalidTokenError`/`ExpiredSignatureError` → caller (`get_current_user`) catch và đổi sang 401.

### `set_auth_cookie(response: Response, token: str) -> None`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/core/security.py:33-43
def set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.jwt_access_expire_minutes * 60,
        path="/",
    )
```

- `httponly=True` chống XSS đọc cookie.
- `secure` theo env (False local, True prod HTTPS).
- `samesite=lax` baseline CSRF.
- `max_age = jwt_access_expire_minutes * 60` đồng bộ với JWT exp.

### `clear_auth_cookie(response: Response) -> None`

Dùng cho `/auth/logout`.

## 4.6 `app/middleware/`

### `middleware/request_context.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/middleware/request_context.py:1-13
from contextvars import ContextVar

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id_ctx.get()


def set_request_id(request_id: str) -> None:
    _request_id_ctx.set(request_id)
```

`ContextVar` → mỗi async task có giá trị riêng (không bị share state giữa request đồng thời). Default `-` để log trước khi middleware set vẫn có giá trị.

### `middleware/request_id.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/middleware/request_id.py:18-51
class RequestIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(self.settings.request_id_header) or str(uuid4())
        set_request_id(request_id)

        start = time.perf_counter()
        logger.info("request.start method=%s path=%s request_id=%s", ...)

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers[self.settings.request_id_header] = request_id
        logger.info("request.end method=%s path=%s status=%s duration_ms=%.2f request_id=%s", ...)
        return response
```

Pipeline mỗi request:
1. Lấy `X-Request-ID` từ header hoặc tự sinh UUID4 (cho phép upstream LB trace cross-service).
2. Set vào `ContextVar` → mọi log trong request có cùng `request_id`.
3. Log cặp `request.start` / `request.end` kèm `duration_ms` (đo qua `time.perf_counter`).
4. Echo `request_id` về response header để client trace dễ.

## 4.7 `app/dependencies/auth.py`

```@d:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api/app/dependencies/auth.py:13-41
def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    settings = get_settings()
    session_token = request.cookies.get(settings.session_cookie_name)
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = verify_access_token(session_token)
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid session") from None

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user
```

Pipeline 3 bước: cookie → JWT decode → DB lookup. Mọi router cần auth dùng `current_user: User = Depends(get_current_user)`.

3 nhánh lỗi map về 401:
- Cookie thiếu → `Not authenticated`.
- Token invalid hoặc `sub` không phải int → `Invalid session`.
- User bị xóa khỏi DB → `User not found`.

`raise ... from None` để Python không print chain exception JWT vào log (giảm noise log production).
