# Phase 10 - Post-MVP

## Outcome
Mở rộng sản phẩm sau khi MVP ổn định và có dữ liệu sử dụng thực tế.

## Candidate tasks

### 10.1 OCR optimization
- Fine-tune rule parse theo vendor/template.
- Hỗ trợ multi-page hoặc multi-upload tốt hơn.

### 10.2 Chat memory RAG (deferred from Phase 7)
- Summarize chat history mỗi N messages.
- Embed summary → chat_memory_chunks table.
- Tool `search_chat_memory` cho hỏi lại mục tiêu/user preference từ conversations cũ.

### 10.3 App knowledge RAG (deferred from Phase 7)
- Tạo knowledge base FAQ + user guide.
- Tool `search_app_knowledge` trả lời câu hỏi hướng dẫn sử dụng.

### 10.4 Export
- Export CSV/PDF cho transaction list hoặc summary.

### 10.5 Merchant learning nâng cao
- Cải thiện mapping merchant-category theo hành vi user.
- Ranking tốt hơn cho category suggestion.

### 10.6 Explainability cho chat answer
- Hiển thị data points / tool calls đứng sau mỗi câu trả lời.
- Tăng độ tin tưởng: user click xem transaction nào được tính vào tổng.

### 10.7 Personalization sâu hơn
- Gợi ý chi tiêu theo chu kỳ cá nhân.
- Cảnh báo bất thường tốt hơn theo lịch sử user.

### 10.8 Multi-provider operations
- Chuyển đổi linh hoạt giữa OCR/LLM/embedding providers theo cost, latency, quality.

### 10.9 Advanced RAG techniques
- Reranking với cross-encoder (bge-reranker).
- Hybrid search BM25 + vector.
- Query rewriting / expansion trước retrieval.

### 10.10 Custom mascot illustrations (deferred from Phase 8)
- Thay emoji placeholder bằng custom SVG mascot.
- Hire designer hoặc dùng illustration library.

## Lưu ý
Chỉ mở phase này khi phase 0-9 đã ổn định, có telemetry cơ bản và có feedback usage thực tế.
