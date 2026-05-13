# Design Document — RAG Extension (Phase 7)

## Overview

Bổ sung RAG capability cho chatbot hiện tại: LLM có thể gọi RAG tools để tìm nội dung OCR hóa đơn và semantic search giao dịch, bên cạnh SQL tools đã có.

### Architecture diff

```
Phase 6 (hiện tại):
User → Chat API → Orchestrator → LLM → SQL tools (7 tools) → PostgreSQL

Phase 7 (sau):
User → Chat API → Orchestrator → LLM → Tool Router
                                       ├─ SQL tools (7 tools)    → PostgreSQL
                                       └─ RAG tools (2 tools)    → PostgreSQL + pgvector
```

## Design Decisions

**Decision 1: pgvector thay vì Chroma/Qdrant**
- Lý do: PostgreSQL đã có sẵn, dataset nhỏ (< 100k vectors/user), tránh thêm service mới.
- Tradeoff: pgvector chậm hơn Qdrant ở scale lớn, nhưng MVP chưa cần.

**Decision 2: Local sentence-transformers thay vì OpenAI embeddings API**
- Model: `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, ~120MB, CPU-friendly, tốt cho tiếng Việt).
- Lý do: free, deterministic, không cần gọi external API cho mỗi receipt.
- Tradeoff: chất lượng embedding thấp hơn OpenAI text-embedding-3-small, nhưng đủ cho use case.

**Decision 3: Index async trong worker, không block upload flow**
- User upload receipt → API response ngay với status PROCESSING → worker OCR → worker embed → chunk ready.
- Chat có thể tìm được sau vài giây. Không làm user đợi.

**Decision 4: Một bảng `receipt_text_chunks`, không tách riêng bảng cho transaction note**
- Note hiện tại ngắn, gộp vào `receipt_text_chunks` với `source_type="receipt_ocr"` hoặc `"transaction_note"`.
- Đơn giản schema, 1 bảng dễ maintain.

**Decision 5: Chunking strategy — conditional split**
- OCR text ≤ 500 chars: embed cả text, không split (single chunk).
- OCR text > 500 chars: split chunks 400 chars, overlap 80 chars.
- Lý do: hầu hết receipt ngắn, over-chunking tạo noise.

**Decision 6: SQL filter trước vector search**
- Luôn filter `user_id` + date/merchant trước khi `ORDER BY embedding <-> query_embedding`.
- Isolation + performance.

## Data Model

### `receipt_text_chunks`

```sql
CREATE TABLE receipt_text_chunks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    receipt_upload_id INTEGER NOT NULL REFERENCES receipt_uploads(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    embedding VECTOR(384) NOT NULL,
    source_type VARCHAR(32) NOT NULL DEFAULT 'receipt_ocr',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_receipt_chunks_user_receipt
    ON receipt_text_chunks(user_id, receipt_upload_id);

-- Vector similarity search index (IVFFlat cho dataset nhỏ)
CREATE INDEX ix_receipt_chunks_embedding
    ON receipt_text_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);
```

### Transaction semantic search — approach

**Option A:** Thêm column `embedding VECTOR(384)` vào `transactions` trực tiếp.
- Ưu: 1 query, không cần join.
- Nhược: migration schema nặng, re-embed khi transaction update.

**Option B:** Tái sử dụng `receipt_text_chunks` với `source_type='transaction_text'` + `transaction_id` column.
- Ưu: 1 bảng, flexible.
- Nhược: cần join khi query.

**Decision: Option A** cho transactions, vì transactions là entity thường xuyên update và embedding gắn chặt với record.

```sql
ALTER TABLE transactions ADD COLUMN search_embedding VECTOR(384);
CREATE INDEX ix_transactions_embedding
    ON transactions USING ivfflat (search_embedding vector_cosine_ops)
    WITH (lists = 50);
```

Khi tạo/update transaction → re-embed `f"{merchant_name} {note or ''}"` → save.

## Module Layout

```
backend/api/app/services/chat/
├── queries.py              # (giữ nguyên 7 SQL tools)
├── rag_queries.py          # MỚI — search_receipt_text, semantic_search_transactions
├── embedding_client.py     # MỚI — Protocol + LocalEmbeddingClient
├── llm_client.py           # (giữ nguyên)
├── orchestrator.py         # (giữ nguyên)
├── safety.py               # (giữ nguyên)
├── system_prompt.py        # update rules RAG
├── tools.py                # update — add 2 RAG tools vào TOOL_REGISTRY

backend/shared/pfa_shared/
└── entities.py             # + ReceiptTextChunk, + Transaction.search_embedding

backend/api/alembic/versions/
├── *_enable_pgvector.py             # MỚI
└── *_add_transaction_embedding.py   # MỚI

backend/worker/
├── tasks.py                # + chain index_receipt_text sau OCR
└── index_tasks.py          # MỚI — index logic tách ra
```

## Components & Interfaces

### 1. Embedding Client

```python
# services/chat/embedding_client.py
from typing import Protocol
from functools import lru_cache

EMBEDDING_DIMENSION = 384
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

class EmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbeddingClient:
    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME) -> None:
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)
        assert self._model.get_sentence_embedding_dimension() == EMBEDDING_DIMENSION

    async def embed(self, text: str) -> list[float]:
        # Run sync model trong thread pool
        import asyncio
        embedding = await asyncio.to_thread(self._model.encode, text)
        return embedding.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        embeddings = await asyncio.to_thread(
            self._model.encode, texts, batch_size=32,
        )
        return [e.tolist() for e in embeddings]


@lru_cache(maxsize=1)
def get_embedding_client() -> EmbeddingClient:
    return LocalEmbeddingClient()
```

### 2. RAG Queries

```python
# services/chat/rag_queries.py

def search_receipt_text(
    session: Session,
    user_id: int,
    *,
    query: str,
    date_range: str | None = None,
    merchant: str | None = None,
    receipt_upload_id: int | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Tìm chunks OCR phù hợp với query."""
    embedding_client = get_embedding_client()

    # Embed query (sync since we're in sync context, but should be async)
    # For MVP: load client at startup, call sync encode directly
    query_embedding = embedding_client.embed_sync(query)

    # SQL filter + vector search
    base = select(ReceiptTextChunk, ReceiptUpload).join(
        ReceiptUpload, ReceiptTextChunk.receipt_upload_id == ReceiptUpload.id
    ).where(ReceiptTextChunk.user_id == user_id)

    if receipt_upload_id:
        base = base.where(ReceiptTextChunk.receipt_upload_id == receipt_upload_id)

    if date_range:
        preset = _resolve_preset(date_range)
        range_ = resolve_range(preset)
        # join transactions if needed for date filter
        # ... filter by receipt.created_at hoặc transaction.date

    if merchant:
        # join transactions to get merchant
        # filter by transaction.merchant_name ILIKE
        pass

    # Vector similarity search
    base = base.order_by(
        ReceiptTextChunk.embedding.cosine_distance(query_embedding)
    ).limit(min(limit, 10))

    rows = session.exec(base).all()

    chunks = [
        {
            "chunk_text": row[0].chunk_text,
            "receipt_upload_id": row[0].receipt_upload_id,
            "similarity": ...,  # compute from distance
        }
        for row in rows
    ]

    return {"chunks": chunks, "query": query}


def semantic_search_transactions(
    session: Session,
    user_id: int,
    *,
    query: str,
    date_range: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    category_name: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Semantic search transactions theo ý nghĩa."""
    # Similar pattern: SQL filter → vector search trên transactions.search_embedding
```

### 3. Index Worker Task

```python
# worker/index_tasks.py
@broker.task
async def index_receipt_text(receipt_upload_id: int) -> None:
    with Session(engine) as session:
        # Load OCR result
        ocr = session.exec(
            select(OcrResult).where(OcrResult.receipt_upload_id == receipt_upload_id)
        ).first()
        if not ocr or not ocr.raw_text:
            return

        receipt = session.get(ReceiptUpload, receipt_upload_id)
        if not receipt:
            return

        # Clean + chunk
        text = clean_ocr_text(ocr.raw_text)
        chunks = chunk_text(text, max_size=400, overlap=80)

        # Embed
        client = get_embedding_client()
        embeddings = await client.embed_batch([c for c in chunks])

        # Persist
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            session.add(ReceiptTextChunk(
                user_id=receipt.user_id,
                receipt_upload_id=receipt_upload_id,
                chunk_text=chunk,
                chunk_index=idx,
                embedding=emb,
                source_type="receipt_ocr",
            ))
        session.commit()
```

### 4. Updated Transaction Flow

```python
# api/v1/transactions.py - update create/update
def _build_search_text(merchant_name: str | None, note: str | None) -> str:
    parts = [p for p in [merchant_name, note] if p]
    return " ".join(parts).strip()

def create_transaction(...):
    # ... existing logic
    search_text = _build_search_text(payload.merchant_name, payload.note)
    if search_text:
        client = get_embedding_client()
        embedding = client.embed_sync(search_text)
        transaction.search_embedding = embedding
    # ... save
```

## Tool Registry Update

```python
TOOL_REGISTRY = {
    # ... existing 7 SQL tools
    "search_receipt_text": ToolDefinition(
        name="search_receipt_text",
        description="Search detailed content within receipt OCR text. Use when user asks about items/services in a specific receipt (food items, services, line items).",
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search in receipt text"},
                "date_range": {"type": "string", "enum": ["7d", "30d", "this_month", "last_month"]},
                "merchant": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
        handler=search_receipt_text,
    ),
    "semantic_search_transactions": ToolDefinition(
        name="semantic_search_transactions",
        description="Search transactions semantically by meaning. Use when keywords are abstract (skincare, travel, pets, medical) that may not match exact DB values.",
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "date_range": {"type": "string", "enum": ["7d", "30d", "this_month", "last_month"]},
                "amount_min": {"type": "number"},
                "amount_max": {"type": "number"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
        handler=semantic_search_transactions,
    ),
}
```

## System Prompt Update

Thêm vào `SYSTEM_PROMPT`:

```
TOOL USAGE RULES:
- Số liệu, tổng, đếm, ranking, budget → dùng SQL tools (query_spending_summary, search_transactions, ...).
- Nội dung chi tiết hóa đơn (món hàng, dịch vụ, phí) → dùng search_receipt_text.
- Tìm theo ý nghĩa mơ hồ (skincare, du lịch, y tế) → dùng semantic_search_transactions.
- Cần cả số liệu + nội dung → gọi cả SQL tool và RAG tool.
- KHÔNG tự tính tổng từ OCR context — dùng SQL tool.
- Nếu RAG context không đủ → nói "chưa đủ dữ liệu", KHÔNG bịa món hàng.
```

## Error Handling

| Scenario | Behavior |
|---|---|
| Embedding model fail to load at startup | App fails fast, log error |
| pgvector extension not installed | Migration fails, clear error message |
| User has 0 receipts → vector search returns empty | Tool returns `{chunks: [], query: ...}`, LLM handles gracefully |
| Embedding dimension mismatch | Raise at LocalEmbeddingClient init |
| Worker task fail (OCR index) | Log + skip; manual re-run via backfill script |

## Testing Strategy

### Unit tests
- `test_embedding_client.py`: mock model, verify dimension, batch size.
- `test_rag_queries.py`: mock embedding, verify SQL filter, user isolation.
- `test_index_tasks.py`: chunk splitting logic, empty OCR handling.

### Integration tests (cần PostgreSQL + pgvector)
- Seed 2 users với receipts có OCR text khác nhau.
- Query "Grab" từ user A → chỉ thấy receipt của A.
- Query "trà sữa" → top result phải chứa từ khóa liên quan.

### Manual acceptance
1. "Hóa đơn Grab ngày X có món gì?" → bot trả đúng món từ OCR.
2. "Tôi có mua đồ skincare không?" → bot tìm được transactions dù không có keyword trực tiếp.
3. "Tìm hóa đơn có mua cà phê" → bot trả các receipt có cà phê.
4. "Cross-user test": user A không thấy receipt user B.
5. "Không đủ dữ liệu": hỏi về receipt chưa có → bot nói "chưa có dữ liệu".

## Performance

- Embed 1 text (CPU, MiniLM 384-dim): ~50-100ms.
- Vector search 10k chunks với ivfflat: ~10-20ms.
- Total chat turn với RAG tool: < 2s overhead.
- Model RAM: ~500MB (loaded once, shared).
