# Implementation Tasks — RAG Extension (Phase 7)

## Prerequisites
- Phase 6 (AI Chatbot) complete và stable.
- LLM endpoint `cx/gpt-5.5` hoạt động.
- PostgreSQL 16 với quyền CREATE EXTENSION.

---

## Task 7.0 — Technical spike (0.5 ngày)

### Steps
1. Verify pgvector install được trên local PostgreSQL:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   SELECT '[1,2,3]'::vector;
   ```
2. Test `sentence-transformers` load + embed:
   ```python
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
   emb = model.encode("Hóa đơn Grab trà đào 45k")
   assert len(emb) == 384
   ```
3. Benchmark: embed 100 texts, đo latency.
4. Quyết định: local model OK → lock dimension 384.

### Validation
- Extension cài được.
- Model load, embed tiếng Việt OK.
- Latency < 200ms/embed trên máy dev.

---

## Task 7.1 — pgvector + entities (0.5 ngày)

### Steps
1. Install deps:
   - `backend/api/pyproject.toml`: thêm `pgvector>=0.2.5`, `sentence-transformers>=2.7.0`.
   - `backend/worker/pyproject.toml`: thêm tương tự.
   - Run `uv sync` (hoặc pip install -e).
2. Alembic migration `enable_pgvector`:
   - `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` up.
   - `op.execute("DROP EXTENSION IF EXISTS vector")` down.
3. Thêm `ReceiptTextChunk` entity vào `pfa_shared/entities.py`:
   ```python
   from pgvector.sqlalchemy import Vector
   
   EMBEDDING_DIMENSION = 384
   
   class ReceiptTextChunk(SQLModel, table=True):
       __tablename__ = "receipt_text_chunks"
       id: int | None = Field(default=None, primary_key=True)
       user_id: int = Field(foreign_key="users.id", index=True)
       receipt_upload_id: int = Field(
           foreign_key="receipt_uploads.id",
           index=True,
           sa_column_kwargs={"ondelete": "CASCADE"},
       )
       chunk_text: str
       chunk_index: int = Field(default=0)
       embedding: list[float] = Field(sa_column=Column(Vector(EMBEDDING_DIMENSION)))
       source_type: str = Field(default="receipt_ocr", max_length=32)
       created_at: datetime = ...
   ```
4. Thêm column `search_embedding` vào `Transaction` entity.
5. Re-export trong `app/models/entities.py`.
6. Migration cho `receipt_text_chunks` + alter `transactions`.
7. Reinstall shared package editable: `pip install -e ../shared`.

### Validation
- `alembic upgrade head` pass.
- Query `SELECT * FROM receipt_text_chunks LIMIT 1` không lỗi.
- Import `ReceiptTextChunk` OK từ API.

---

## Task 7.2 — Embedding client (1 ngày)

### Steps
1. Tạo `backend/api/app/services/chat/embedding_client.py`:
   - `EMBEDDING_DIMENSION = 384`.
   - `EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"`.
   - Protocol `EmbeddingClient`.
   - `LocalEmbeddingClient` class với `embed_sync`, `embed`, `embed_batch`.
   - `get_embedding_client()` singleton với `lru_cache`.
2. Copy module sang worker (hoặc tạo shared package).
3. Unit tests: mock model, verify batch output, dimension.

### Validation
- `pytest tests/test_embedding_client.py` pass.
- Import + encode text không crash.

---

## Task 7.3 — Index pipeline worker (1 ngày)

### Steps
1. Tạo `backend/worker/index_tasks.py`:
   - `clean_ocr_text(text)` — strip extra whitespace, normalize.
   - `chunk_text(text, max_size, overlap)` — conditional: ≤500 chars no split.
   - Task `index_receipt_text(receipt_upload_id)`.
2. Chain sau OCR task trong `worker/tasks.py`:
   ```python
   await index_receipt_text.kiq(receipt_upload_id)
   ```
3. Script backfill `backend/api/scripts/backfill_receipt_embeddings.py`:
   - Query tất cả `OcrResult` chưa có chunks.
   - For each: gọi embed + save chunks.
4. Tests: chunk split logic, empty OCR handling, idempotent (chạy 2 lần không duplicate).

### Validation
- Upload receipt thật → sau OCR, `receipt_text_chunks` có data.
- Backfill chạy được trên DB có sẵn receipts.

---

## Task 7.4 — Transaction embedding (0.5 ngày)

### Steps
1. Helper `_build_search_text(merchant_name, note)`.
2. Update `api/v1/transactions.py`:
   - `create_transaction`: embed `search_text` → save `transaction.search_embedding`.
   - `update_transaction`: re-embed nếu `merchant_name` hoặc `note` thay đổi.
3. Script backfill `backfill_transaction_embeddings.py`.

### Validation
- Tạo transaction mới → `search_embedding` có vector.
- Update merchant_name → re-embed.

---

## Task 7.5 — RAG tool: search_receipt_text (1 ngày)

### Steps
1. Tạo `services/chat/rag_queries.py` với `search_receipt_text`:
   - SQL filter user_id + optional date_range + merchant + receipt_id.
   - Vector search `ORDER BY embedding <-> query_embedding LIMIT N`.
   - Return chunks với metadata.
2. Register vào `TOOL_REGISTRY` trong `tools.py`.
3. Unit tests: user isolation, empty result, filter combinations.

### Validation
- Integration test: seed receipt + OCR + chunks → query → trả đúng chunks.

---

## Task 7.6 — RAG tool: semantic_search_transactions (1 ngày)

### Steps
1. Thêm `semantic_search_transactions` vào `rag_queries.py`:
   - SQL filter + vector search trên `transactions.search_embedding`.
2. Register tool vào `TOOL_REGISTRY`.
3. Unit tests.

### Validation
- Query "skincare" → tìm được Watsons/Guardian transactions dù không chứa "skincare".

---

## Task 7.7 — System prompt + docs (0.5 ngày)

### Steps
1. Update `services/chat/system_prompt.py` với RAG rules.
2. Update `tasks/phase-7-rag-extension.md` với progress.
3. Update `README.md` section "RAG Setup".
4. Update `.env.example` với embedding settings (nếu có).

---

## Task 7.8 — Testing & acceptance (1 ngày)

### Manual acceptance checklist
- [ ] "Hóa đơn Grab ngày X có món gì?" → trả đúng món
- [ ] "Tôi có mua cà phê tuần này không?" → tìm được từ OCR
- [ ] "Tôi có mua đồ skincare không?" → semantic match Watsons/Guardian
- [ ] Cross-user isolation: A không thấy receipt B
- [ ] "Khoản này có bất thường không?" → bot combine SQL (amount) + RAG (receipt content)
- [ ] Empty: receipt không có OCR → bot nói "chưa có dữ liệu"

### Unit/integration tests
- [ ] test_embedding_client.py pass
- [ ] test_rag_queries.py pass (user isolation)
- [ ] test_index_tasks.py pass
- [ ] backend ruff + mypy + pytest all green
- [ ] frontend không bị ảnh hưởng

---

## Tổng thời gian
**Core (7.0-7.8): 6-7 ngày làm việc**
