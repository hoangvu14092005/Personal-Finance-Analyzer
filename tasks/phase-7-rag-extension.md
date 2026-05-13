# Phase 7 - RAG Extension for AI Chatbot

## Mục tiêu
Mở rộng chatbot từ function calling trên dữ liệu structured sang hybrid retrieval, kết hợp SQL tools và RAG tools để trả lời các câu hỏi về nội dung phi cấu trúc (OCR hóa đơn, transaction note).

## Nguyên tắc
- SQL vẫn là source of truth cho số liệu, tổng, đếm, ranking, budget.
- RAG chỉ dùng để tìm ngữ cảnh văn bản.
- Luôn filter theo user_id trước khi vector search.
- Không để LLM truy cập vector DB trực tiếp; luôn qua tool layer.
- Không dùng RAG để tự tính tổng tiền.
- Nếu context không đủ, bot phải nói không đủ dữ liệu.

## Scope MVP (Phase 7)

### Tool mới
- `search_receipt_text` — tìm nội dung chi tiết trong OCR hóa đơn
- `semantic_search_transactions` — semantic search transactions theo ý nghĩa

### Infrastructure
- `pgvector` extension PostgreSQL
- `sentence-transformers` local model (paraphrase-multilingual-MiniLM-L12-v2, 384-dim)
- Entity `ReceiptTextChunk`
- Column `transactions.search_embedding`
- Worker task `index_receipt_text` chain sau OCR

## Defer sang Phase 8+
- `search_app_knowledge` (cần knowledge base trước)
- `search_chat_memory` (context window còn dư)
- Category explanation RAG (UserMerchantMapping đã giải quyết)
- Reranking cross-encoder
- Hybrid search BM25 + vector

## Task breakdown
Chi tiết: `.kiro/specs/rag-extension/tasks.md`

1. Technical spike — verify pgvector + sentence-transformers
2. pgvector extension + ReceiptTextChunk entity
3. Embedding client abstraction
4. Index pipeline trong worker
5. Transaction embedding
6. RAG tool: search_receipt_text
7. RAG tool: semantic_search_transactions
8. System prompt update + docs
9. Testing & acceptance

## Exit criteria
- User hỏi "Hóa đơn Grab ngày X có món gì?" → bot trả đúng từ OCR text
- User hỏi "Tôi có mua đồ skincare không?" → bot semantic match được
- Không leak data giữa users
- Manual 10 câu hỏi sample pass
- Backend tests xanh, frontend build xanh

## Ước tính
6-7 ngày làm việc.
