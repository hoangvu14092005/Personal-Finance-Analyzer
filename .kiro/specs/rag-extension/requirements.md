# Requirements Document — RAG Extension (Phase 7)

## Introduction

Mở rộng AI Chatbot (Phase 6) từ **function calling + SQL** sang **function calling + SQL + RAG**.
RAG được thêm như một nhóm tool bổ sung, không thay thế SQL tools.

### Nguyên tắc
- SQL tools: source of truth cho số liệu, tổng, đếm, ranking, budget.
- RAG tools: tìm nội dung phi cấu trúc (OCR text, transaction note).
- LLM: điều phối, gọi đúng tool, tổng hợp câu trả lời.
- Filter `user_id` **trước** khi vector search (isolation bắt buộc).

### Scope Phase 7 (MVP)
- Use case 1: tìm nội dung chi tiết trong hóa đơn OCR.
- Use case 2: semantic search giao dịch theo ý nghĩa mơ hồ.

### Defer sang Phase 8+
- App knowledge RAG (cần knowledge base trước).
- Chat memory RAG (context window còn dư, chưa cần).
- Category explanation RAG (đã có `UserMerchantMapping`).
- Reranking cross-encoder.
- Hybrid search BM25 + vector.

## Requirements

### Requirement 1: pgvector infrastructure

**User Story:** Là developer, tôi cần PostgreSQL hỗ trợ vector search để query embedding hiệu quả.

#### Acceptance Criteria
1. THE system SHALL enable `pgvector` extension trong PostgreSQL 16 qua Alembic migration.
2. THE migration SHALL reversible (up/down).
3. THE system SHALL install package `pgvector` Python trong cả API và Worker dependencies.

### Requirement 2: ReceiptTextChunk entity

**User Story:** Là developer, tôi cần entity lưu chunk OCR + embedding vector.

#### Acceptance Criteria
1. THE entity `ReceiptTextChunk` SHALL nằm trong `pfa_shared/entities.py` để API và Worker dùng chung.
2. THE entity SHALL có các cột: id (int PK), user_id FK, receipt_upload_id FK, chunk_text, embedding (VECTOR), chunk_index, created_at.
3. THE embedding dimension SHALL được lock bằng const module-level (vd: 384 cho multilingual MiniLM).
4. THE entity SHALL có foreign key CASCADE delete khi receipt bị xóa.
5. THE entity SHALL có index (user_id, receipt_upload_id) cho SQL filter nhanh.

### Requirement 3: Embedding client

**User Story:** Là developer, tôi cần client tách biệt để embed text, có thể swap provider.

#### Acceptance Criteria
1. THE embedding client SHALL implement Protocol với `embed(text)` và `embed_batch(texts)`.
2. THE system SHALL default dùng local `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384-dim, free, chạy CPU, tốt cho tiếng Việt).
3. THE dimension SHALL khớp với entity VECTOR column; mismatch → raise lỗi ở startup.
4. THE client SHALL log embed request count, latency, batch size.
5. THE client SHALL cache model instance (lru_cache hoặc module-level) để không load lại mỗi request.

### Requirement 4: Index pipeline

**User Story:** Là user, sau khi upload receipt và OCR xong, nội dung phải được embed tự động để chatbot tìm được.

#### Acceptance Criteria
1. THE worker SHALL có task `index_receipt_text(receipt_id)` chain sau task OCR.
2. THE task SHALL load OCR raw_text, split thành chunks (nếu text > 500 chars), embed, save vào `ReceiptTextChunk`.
3. WHERE OCR text ngắn (≤ 500 chars), task SHALL embed cả text thành 1 chunk duy nhất.
4. THE system SHALL có script backfill `scripts/backfill_receipt_embeddings.py` cho receipts đã có OCR nhưng chưa index.
5. WHEN receipt hoặc OCR result bị xóa, chunks SHALL auto-delete qua CASCADE.

### Requirement 5: RAG tool — search_receipt_text

**User Story:** Khi user hỏi "Hóa đơn Grab hôm qua có món gì?", bot phải tìm được từ OCR text.

#### Acceptance Criteria
1. THE tool signature SHALL accept: user_id, query (text), date_range (optional preset), merchant (optional), receipt_upload_id (optional), limit (default 5).
2. THE tool SHALL SQL filter theo user_id **trước** vector search (mandatory).
3. THE tool SHALL vector search với cosine distance `<->` trong pgvector.
4. THE tool SHALL return chunks kèm metadata (receipt_id, merchant_name, transaction_date, amount, similarity_score).
5. THE tool SHALL respect limit (max 10 để tránh context flood).
6. THE tool SHALL được đăng ký trong `TOOL_REGISTRY` và expose qua OpenAI tool schema.

### Requirement 6: RAG tool — semantic_search_transactions

**User Story:** Khi user hỏi "Tôi có mua đồ skincare không?", bot phải tìm được dù không có keyword "skincare" trực tiếp.

#### Acceptance Criteria
1. THE system SHALL embed `merchant_name + note` khi tạo/update transaction (field mới trong table `transactions` hoặc chunk riêng).
2. THE tool signature SHALL accept: user_id, query, date_range, amount_min, amount_max, category_name, limit (default 10).
3. THE tool SHALL kết hợp SQL filter (user_id, date, amount, category) và vector search trên embedding.
4. THE tool SHALL return transactions với similarity_score để UI/LLM biết độ liên quan.

### Requirement 7: System prompt update

**User Story:** LLM phải biết khi nào dùng SQL vs RAG để không gọi sai tool.

#### Acceptance Criteria
1. THE system prompt SHALL mô tả rõ: "nội dung chi tiết hóa đơn (món hàng, dịch vụ) → dùng search_receipt_text".
2. THE system prompt SHALL cấm "tự tính tổng/đếm từ OCR context — dùng SQL tools".
3. THE system prompt SHALL yêu cầu "nếu OCR không rõ, nói chưa đủ dữ liệu thay vì bịa".

### Requirement 8: Testing

**User Story:** Team cần test coverage để tự tin deploy.

#### Acceptance Criteria
1. Unit tests SHALL cover embedding client với mock model.
2. Unit tests SHALL verify tool user_id isolation (user A không thấy receipt user B).
3. Integration tests với PostgreSQL + pgvector SHALL verify end-to-end search.
4. Manual acceptance: 5 câu hỏi sample về nội dung hóa đơn → bot trả lời đúng, không bịa.
