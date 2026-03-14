## Ghi chú định hướng
Tài liệu gốc mô tả khá rõ các khối hệ thống bắt buộc như web app, backend API, OCR processing, analytics summary, AI insight service, database, object storage, queue worker và cache. Vì vậy stack dưới đây được tối ưu theo mục tiêu:
- dễ cho AI đọc và sinh code,
- triển khai local nhanh,
- scale tách riêng frontend/backend/worker,
- giữ chi phí OCR và AI linh hoạt theo từng môi trường.

## Kết luận kiến trúc được chọn
- **Frontend**: Next.js 15 + TypeScript.
- **Backend API**: FastAPI + Pydantic + SQLModel.
- **Worker**: TaskIQ ưu tiên, Celery là fallback nếu cần hệ sinh thái lớn hơn.
- **Queue/Broker/Cache**: Redis 7.x.
- **Database**: PostgreSQL 16.x.
- **Storage**: MinIO local, S3-compatible ở production.
- **OCR**: adapter interface, ưu tiên PaddleOCR; EasyOCR là fallback; Google Vision là dự phòng cloud.
- **AI Insight**: ưu tiên gọi trực tiếp provider adapter để đơn giản; chỉ dùng LangChain khi thật sự cần multi-provider workflow phức tạp.

---

## Ngôn ngữ và Runtime

### Backend
- **Python**: `3.12+`
- Lý do:
  - Type hints giúp AI sinh code và refactor tốt hơn.
  - FastAPI, Pydantic, SQLModel, pytest, Ruff tạo thành hệ sinh thái cực hợp cho vibecoding.
  - Dễ tích hợp OCR/LLM worker.

### Frontend
- **TypeScript**: `5.6.x`
- **Node.js**: `20 LTS` hoặc `22 LTS` nếu team đã kiểm thử ổn với Next.js 15.
- Ghi chú:
  - Với bài toán này, mình nghiêng mạnh về **Next.js + TypeScript** hơn là frontend Python như Reflex, vì dashboard, upload flow, interactive tables và charting sẽ linh hoạt hơn.
  - Reflex chỉ nên cân nhắc nếu team muốn all-Python tuyệt đối và chấp nhận trade-off về hệ sinh thái frontend.

### Package Manager
- **Python package manager**: `uv`
- **Frontend package manager**: `pnpm` hoặc `npm`; ưu tiên `pnpm` nếu repo lớn, còn `npm` là đủ cho MVP.
- Nhận định:
  - `uv` là lựa chọn rất tốt cho Python và Docker build.
  - Không nên ép frontend cũng dùng uv; frontend vẫn nên dùng package manager JavaScript chuẩn.

---

## Frontend

### Framework
- **Next.js**: `15.x` (App Router)
- **React**: `19.x`
- **TypeScript**: strict mode = `true`

### Styling
- **Tailwind CSS**: `3.4.x`

### State Management / Data Fetching
- **Ưu tiên**: `TanStack Query` cho server-state
- **Dùng thêm**: React Context cho auth/session, theme hoặc UI global state nhỏ
- Nhận định:
  - Không nên dùng Context cho toàn bộ data fetching vì sẽ nhanh rối khi có receipts, transactions, dashboard, budgets, insights.
  - TanStack Query hợp hơn cho cache, refetch, optimistic updates và polling OCR job status.

### Form & Validation phía UI
- Có thể dùng:
  - `react-hook-form`
  - `zod` chỉ ở frontend nếu cần validate UX-friendly trước khi submit
- Tuy nhiên schema nguồn chuẩn vẫn phải nằm ở backend/Pydantic.

---

## Backend API

### Framework
- **FastAPI**: `0.115+`
- Lý do:
  - Hiệu năng tốt.
  - Tự sinh Swagger/OpenAPI.
  - Async/await phù hợp với upload, polling, OCR orchestration.
  - Cực hợp với Pydantic và type hints.

### Validation
- **Pydantic**: `2.x`
- Mục tiêu:
  - request/response schema chặt chẽ,
  - settings parsing,
  - OCR normalized output schema,
  - AI insight structured output schema.

### ORM / Data Layer
- **SQLModel**
- **SQLAlchemy 2.x** là nền bên dưới
- Lý do:
  - Cân bằng tốt giữa ORM model và Pydantic-style schema.
  - Rất thân thiện với AI khi đọc và sinh CRUD/service code.
- Gợi ý thực tế:
  - Nếu gặp giới hạn của SQLModel ở query quá phức tạp, giữ SQLModel cho entity cơ bản và dùng SQLAlchemy Core/ORM cho aggregation query nặng.

### Auth
- **PyJWT** qua **HttpOnly Cookies**
- Thêm:
  - password hashing bằng `pwdlib` hoặc `passlib`/`bcrypt`
  - CSRF strategy nếu app chạy cùng domain/subdomain cần bảo vệ form mutation
- Session model đề xuất:
  - access token ngắn hạn,
  - refresh token xoay vòng,
  - cookie `HttpOnly`, `Secure`, `SameSite=Lax` hoặc `Strict` tùy flow.

### API Style
- REST JSON
- Versioned routes: `/api/v1/...`
- OpenAPI là contract chính giữa frontend và backend.

---

## Worker / Queue

### Task Queue
- **Ưu tiên**: `TaskIQ`
- **Fallback**: `Celery`

### Broker / Cache
- **Redis**: `7.x`

### Job Types
- `process_ocr_job`: trích xuất dữ liệu từ ảnh receipt.
- `refresh_analytics_job`: recompute cache/summary sau khi transaction thay đổi.
- `generate_insight_job`: gọi LLM hoặc rule engine tạo insight.

### Khuyến nghị lựa chọn
- Dùng **TaskIQ** cho MVP nếu muốn codebase hiện đại, gọn, async-native và gần FastAPI hơn.
- Chuyển sang **Celery** chỉ khi cần scheduling/phân tán/phụ trợ phức tạp hơn hoặc team đã quen Celery.

---

## Database & Storage

### Database
- **PostgreSQL**: `16.x`

### Storage
- **Local**: `MinIO`
- **Production**: `S3-compatible storage`

### Quy ước lưu trữ
- Receipt image lưu object storage.
- DB chỉ lưu metadata, status, extracted text, normalized payload, transaction records, budget records, insight snapshots.
- Không lưu raw image trong database.

---

## OCR Processing

### Kiến trúc OCR
- Tạo interface: `OCRProvider`
- Các method gợi ý:
  - `extract_text(file_path: str) -> OCRRawResult`
  - `normalize_receipt(raw: OCRRawResult) -> OCRNormalizedReceipt`

### Provider local
- **Ưu tiên**: `PaddleOCR`
- **Fallback**: `EasyOCR`

### Cloud provider dự phòng
- **Google Vision API**

### Nhận định kỹ thuật
- PaddleOCR thường hợp hơn cho pipeline OCR nghiêm túc, nhưng nặng hơn trong môi trường local nhỏ.
- EasyOCR dễ thử nghiệm nhanh hơn nhưng độ ổn định có thể kém hơn tùy ngôn ngữ/chất lượng ảnh.
- Với MVP, nên làm theo 3 bước:
  1. mock OCR provider,
  2. local OCR provider,
  3. cloud fallback provider.

---

## LLM / AI Insight

### Mục tiêu
AI không đọc ảnh thô, mà đọc structured financial summary hoặc transaction aggregates.

### Provider / Library
- **Ưu tiên kiến trúc**: custom provider adapter mỏng
- **Local brain**: `Ollama` (Llama 3 hoặc Qwen 2.5 qua local API)
- **Cloud brain tiết kiệm**: Google Generative AI SDK cho Gemini
- **LangChain hoặc Haystack**:
  - chỉ dùng khi cần workflow chaining, prompt templates nhiều tầng, tracing hay provider abstraction phức tạp.

### Khuyến nghị thực tế
- Cho MVP, **không nên bắt đầu bằng LangChain/Haystack**.
- Nên bắt đầu bằng:
  - prompt templates lưu file markdown/yaml,
  - Pydantic structured output parser,
  - provider adapters riêng cho Ollama/Gemini.
- Khi luồng insight đủ phức tạp mới cân nhắc thêm LangChain.

### Output contract
- Bắt buộc structured JSON/Pydantic schema.
- Có timeout, retry, cache theo `user_id + time_range + data_fingerprint`.
- Có fallback rule-based insight khi LLM lỗi.

---

## Testing & Quality

### Test
- **Unit/Integration**: `pytest`
- **API contract/integration**: `httpx`, `pytest-asyncio`
- **Frontend E2E**: `Playwright`

### Lint / Format
- **Ruff**
- Ghi chú:
  - Ruff có thể thay phần lớn Flake8 + isort và nhiều rule lint khác.
  - Nếu cần format, dùng thêm `ruff format` là đủ trong đa số trường hợp.

### Type Check
- **mypy**

### Frontend quality
- **ESLint** đi kèm Next.js
- **Prettier** optional; nếu team muốn ít tool hơn có thể chỉ giữ ESLint + quy ước code style rõ ràng.

---

## Observability

### Logging
- Python logging chuẩn hoặc `structlog`
- Ưu tiên log có correlation id / request id / job id

### Metrics
- `prometheus-client`
- Theo dõi:
  - OCR latency
  - AI latency
  - queue depth
  - upload failure rate
  - API response time
  - dashboard cache hit rate

### Error Tracking
- `Sentry` ở phase hardening/release

---

## Container & Local Environment

### Môi trường local đề xuất
- Frontend app
- FastAPI app
- Worker app
- PostgreSQL 16
- Redis 7
- MinIO
- Mock hoặc local OCR provider
- Mock hoặc local/cloud LLM provider

### Docker
- Docker Engine `26+`
- Docker Compose v2
- Multi-stage Dockerfiles cho frontend/api/worker

### Config
- `.env`
- `.env.example` bắt buộc đầy đủ
- Tách nhóm biến: app, auth, db, redis, storage, OCR, LLM, observability

---

## Phiên bản đề xuất tóm tắt

### Backend
- Python `3.12+`
- FastAPI `0.115+`
- Pydantic `2.x`
- SQLModel `0.0.x` compatible với SQLAlchemy 2
- PostgreSQL `16.x`
- Redis `7.x`
- TaskIQ `latest stable` hoặc Celery `5.x`
- pytest `8.x`
- Ruff `0.6+`
- mypy `1.x`

### Frontend
- Node.js `20 LTS`
- TypeScript `5.6.x`
- Next.js `15.x`
- React `19.x`
- Tailwind CSS `3.4.x`
- TanStack Query `5.x`
- Playwright `1.5x`

### AI / OCR
- Ollama `latest stable`
- Google Generative AI SDK `latest stable`
- PaddleOCR hoặc EasyOCR
- Google Vision API làm fallback

---

## Biến môi trường đề xuất

### App
- `APP_ENV`
- `API_V1_PREFIX`
- `WEB_URL`
- `API_URL`

### Auth
- `JWT_SECRET`
- `JWT_ACCESS_EXPIRE_MINUTES`
- `JWT_REFRESH_EXPIRE_DAYS`
- `SESSION_COOKIE_NAME`
- `SESSION_COOKIE_SECURE`
- `SESSION_COOKIE_SAMESITE`

### Database / Cache
- `DATABASE_URL`
- `REDIS_URL`

### Storage
- `S3_ENDPOINT`
- `S3_REGION`
- `S3_BUCKET_PRIVATE`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`

### OCR
- `OCR_PROVIDER`
- `OCR_TIMEOUT_MS`
- `OCR_MAX_FILE_SIZE_MB`
- `GOOGLE_VISION_API_KEY`

### AI
- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY`
- `LLM_TIMEOUT_MS`
- `LLM_MAX_RETRIES`
- `OLLAMA_BASE_URL`

### Observability
- `LOG_LEVEL`
- `SENTRY_DSN`
- `PROMETHEUS_ENABLED`

---

## Dependency rules
- Không cài package chỉ để tiện tay.
- Mỗi dependency phải trả lời được:
  1. giải quyết vấn đề gì,
  2. có thể thay bằng built-in không,
  3. có làm tăng lock-in không,
  4. có tăng bundle/runtime cost không,
  5. AI có thể bảo trì/refactor nó ổn không.

## Tương thích với KPI/NFR
- Dashboard first load <= 2s với dưới ngưỡng dữ liệu MVP.
- OCR preview <= 8s cho ảnh chuẩn.
- Save transaction <= 1s.
- AI summary <= 5s sau khi summary data sẵn sàng.
- OCR và AI phải degrade gracefully khi provider lỗi.
- Frontend, API và Worker có thể scale độc lập.
