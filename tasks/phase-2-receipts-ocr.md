# Phase 2 - Receipt Upload & OCR Pipeline

## Outcome
User upload được receipt, backend lưu metadata và file, worker xử lý OCR bất đồng bộ, frontend xem được draft extraction hoặc fallback lỗi.

## Task breakdown

### 2.1 Receipt domain & status model
- Hoàn thiện SQLModel `ReceiptUpload` và `OcrResult`.
- Chuẩn hóa enum trạng thái:
  - uploaded
  - processing
  - ready
  - failed
- Acceptance:
  - Trạng thái xử lý rõ ràng và có thể poll từ frontend.

### 2.2 File validation rules
- Hỗ trợ JPG/PNG/PDF 1 trang trong MVP.
- Validate MIME type, size limit, extension.
- Từ chối file invalid với lỗi rõ ràng.
- Acceptance:
  - File lỗi bị chặn từ API.

### 2.3 Storage service
- Tạo storage abstraction cho MinIO/S3.
- Tạo path convention theo `user_id/receipt_id`.
- Thêm upload/delete helper.
- Acceptance:
  - API lưu file thành công vào storage local.

### 2.4 Upload API
- `POST /receipts/upload`
- Tạo receipt record trong DB.
- Upload file vào storage.
- Enqueue `process_ocr_job`.
- Acceptance:
  - Upload xong nhận được `receipt_id` và status ban đầu.

### 2.5 OCR provider abstraction
- Tạo abstract provider `OCRProvider`.
- Viết `MockOCRProvider` cho dev/test.
- Viết `PaddleOCRProvider` hoặc `EasyOCRProvider` ở mức baseline.
- Acceptance:
  - Có thể đổi provider qua config mà không sửa business flow.

### 2.6 OCR normalization service
- Parse raw OCR output thành fields chuẩn:
  - merchant
  - transaction_date
  - total_amount
  - currency
  - line items optional
- Gắn confidence cho field nếu provider hỗ trợ.
- Acceptance:
  - Output normalized đủ để render draft review.

### 2.7 TaskIQ OCR worker job
- Tạo `process_ocr_job(receipt_id)`.
- Load receipt record + file object.
- Gọi OCR provider.
- Lưu `OcrResult` + update receipt status.
- Acceptance:
  - Worker xử lý thành công receipt thật hoặc mock.

### 2.8 Status polling APIs
- `GET /receipts/{receipt_id}`
- `GET /receipts/{receipt_id}/ocr-result`
- Acceptance:
  - Frontend poll được trạng thái và dữ liệu OCR.

### 2.9 Frontend upload flow
- Tạo upload form/dropzone.
- Hiển thị progress state: uploading, processing, ready, failed.
- Chuyển đến draft review khi OCR xong.
- Acceptance:
  - User đi được luồng upload -> chờ -> xem kết quả.

### 2.10 Error handling & fallback
- Khi OCR fail, hiển thị fallback sang manual entry.
- Lưu error code/message nội bộ.
- Không crash dashboard/app shell.
- Acceptance:
  - OCR fail vẫn giữ được receipt record và UX rõ ràng.

### 2.11 Tests
- Backend integration test upload API.
- Worker tests cho OCR job.
- Frontend E2E upload flow với mock OCR.
- Acceptance:
  - Pipeline OCR pass ở môi trường dev/test.

## Exit criteria phase 2
- Upload và OCR async hoạt động end-to-end.
- Có mock provider để vibecoding nhanh.
- Có fallback rõ ràng khi OCR lỗi.
