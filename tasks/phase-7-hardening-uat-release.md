# Phase 7 - Hardening, UAT & Release

## Outcome
Sản phẩm đạt mức đủ ổn định để UAT và release MVP với rủi ro có kiểm soát.

## Task breakdown

### 7.1 Observability baseline
- Hoàn thiện logging cho:
  - auth
  - upload
  - OCR jobs
  - transaction mutations
  - insight jobs
- Thêm correlation id xuyên API -> worker.
- Acceptance:
  - Có thể trace luồng lỗi end-to-end.

### 7.2 Metrics & operational visibility
- Đo ít nhất:
  - API latency
  - job failure rate
  - queue depth
  - OCR processing time
  - insight generation time
- Acceptance:
  - Có dữ liệu cơ bản để debug hiệu năng và stability.

### 7.3 Error handling & retries
- Chuẩn hóa API error response.
- Thêm timeout/retry cho OCR và AI providers.
- Đảm bảo idempotency hợp lý cho upload/job generate.
- Acceptance:
  - Partial failure không làm mất dữ liệu quan trọng.

### 7.4 Security hardening
- Rà soát quyền truy cập theo `user_id`.
- Đảm bảo auth cookie flags đúng theo môi trường.
- Không để lộ object path/storage public không cần thiết.
- Rà soát log không chứa dữ liệu nhạy cảm quá mức.
- Acceptance:
  - Pass self-review security checklist MVP.

### 7.5 Performance tuning
- Tối ưu query dashboard.
- Thêm indexes cần thiết.
- Tinh chỉnh worker concurrency.
- Tối ưu frontend loading waterfall nếu có.
- Acceptance:
  - Các luồng chính phản hồi mượt trên dataset MVP.

### 7.6 UAT checklist
- Viết checklist cho các luồng:
  - register/login/logout
  - upload receipt
  - OCR success/fail
  - manual entry
  - transaction CRUD
  - dashboard filters
  - budgets
  - AI insights
- Acceptance:
  - QA/BA/UAT có thể chạy checklist mà không cần suy đoán.

### 7.7 Regression & bug fixing
- Chạy regression sau mỗi bugfix quan trọng.
- Fix blocker/critical/high trước.
- Acceptance:
  - Không còn blocker/critical mở.

### 7.8 Deployment runbook
- Viết checklist env staging/prod.
- Viết migration rollout notes.
- Viết rollback notes.
- Viết secret/config matrix tối thiểu.
- Acceptance:
  - Có tài liệu deploy rõ ràng cho MVP.

## Exit criteria phase 7
- Pass UAT các luồng chính.
- Không còn lỗi gây sai dữ liệu tài chính hoặc lộ dữ liệu.
- Có thể deploy staging/prod với runbook rõ ràng.
