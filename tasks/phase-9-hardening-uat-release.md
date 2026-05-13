# Phase 9 - Hardening, UAT & Release

## Outcome
Sản phẩm đạt mức đủ ổn định để UAT và release MVP với rủi ro có kiểm soát.

## Task breakdown

### 9.1 Observability baseline
- Hoàn thiện logging cho:
  - auth
  - upload
  - OCR jobs
  - transaction mutations
  - chat turns (user_id, tool_calls_count, tokens_used, duration_ms)
  - RAG index tasks
- Thêm correlation id xuyên API -> worker.
- Acceptance:
  - Có thể trace luồng lỗi end-to-end.

### 9.2 Metrics & operational visibility
- Đo ít nhất:
  - API latency
  - job failure rate
  - queue depth
  - OCR processing time
  - chat turn duration + tool_calls_count distribution
  - embedding latency + vector search latency
- Acceptance:
  - Có dữ liệu cơ bản để debug hiệu năng và stability.

### 9.3 Error handling & retries
- Chuẩn hóa API error response.
- Thêm timeout/retry cho OCR, LLM và embedding providers.
- Đảm bảo idempotency hợp lý cho upload/index jobs.
- Acceptance:
  - Partial failure không làm mất dữ liệu quan trọng.

### 9.4 Security hardening
- Rà soát quyền truy cập theo `user_id` (đặc biệt chat tools + RAG queries).
- Đảm bảo auth cookie flags đúng theo môi trường.
- Không để lộ object path/storage public không cần thiết.
- Rà soát log không chứa dữ liệu nhạy cảm quá mức (chat content, receipt OCR text).
- Rate limit chat endpoint đã deploy (Phase 6 đã có in-memory, xem xét Redis cho multi-instance).
- Acceptance:
  - Pass self-review security checklist MVP.

### 9.5 Performance tuning
- Tối ưu query dashboard.
- Thêm indexes cần thiết.
- Tinh chỉnh worker concurrency.
- Tinh chỉnh pgvector ivfflat lists parameter theo data size.
- Tối ưu frontend loading waterfall nếu có.
- Acceptance:
  - Các luồng chính phản hồi mượt trên dataset MVP.

### 9.6 UAT checklist
- Viết checklist cho các luồng:
  - register/login/logout
  - upload receipt
  - OCR success/fail
  - manual entry
  - transaction CRUD
  - dashboard filters
  - budgets
  - chat: câu hỏi số liệu, câu hỏi về receipt content (RAG), câu hỏi out-of-scope
- Acceptance:
  - QA/BA/UAT có thể chạy checklist mà không cần suy đoán.

### 9.7 Regression & bug fixing
- Chạy regression sau mỗi bugfix quan trọng.
- Fix blocker/critical/high trước.
- Acceptance:
  - Không còn blocker/critical mở.

### 9.8 Deployment runbook
- Viết checklist env staging/prod.
- Viết migration rollout notes.
- Viết rollback notes.
- Viết secret/config matrix tối thiểu (bao gồm CHAT_LLM_API_KEY, embedding model cache path).
- Viết note về pgvector extension requirement.
- Acceptance:
  - Có tài liệu deploy rõ ràng cho MVP.

## Exit criteria phase 9
- Pass UAT các luồng chính (bao gồm chat + RAG).
- Không còn lỗi gây sai dữ liệu tài chính hoặc lộ dữ liệu.
- Có thể deploy staging/prod với runbook rõ ràng.
