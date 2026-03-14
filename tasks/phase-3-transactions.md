# Phase 3 - Transactions & Review

## Outcome
User có thể review OCR draft, sửa field, lưu transaction chính thức hoặc nhập tay hoàn toàn.

## Task breakdown

### 3.1 Transaction domain & schemas
- Hoàn thiện SQLModel `Transaction`, `Category`, `UserMerchantMapping`.
- Tạo Pydantic create/update/list schemas.
- Rule: chỉ transaction đã xác nhận mới vào dashboard summary.
- Acceptance:
  - Schema đủ cho CRUD và analytics.

### 3.2 Draft review payload builder
- Tạo backend payload gộp từ `ReceiptUpload + OcrResult + suggested_category`.
- Trả confidence nếu có.
- Acceptance:
  - Frontend có đủ dữ liệu để render review form.

### 3.3 Category suggestion service
- Tạo baseline mapping từ merchant -> category.
- Fallback `Uncategorized`.
- Lưu mapping khi user chỉnh category.
- Acceptance:
  - Mỗi draft luôn có category đề xuất hoặc fallback rõ ràng.

### 3.4 Draft review UI
- Tạo form review cho:
  - amount
  - date
  - merchant
  - category
  - notes
- Highlight field nghi ngờ low confidence.
- Acceptance:
  - User chỉnh sửa xong và sẵn sàng save transaction.

### 3.5 Create transaction API
- `POST /transactions`
- Cho phép tạo từ OCR draft hoặc manual entry.
- Link optional `receipt_id`.
- Trigger analytics refresh event.
- Acceptance:
  - Save transaction thành công và dữ liệu persisted đúng.

### 3.6 Manual entry UI
- Tạo form nhập tay không cần receipt.
- Reuse validation logic từ backend schemas.
- Acceptance:
  - User có thể tạo giao dịch trong một form gọn.

### 3.7 Update transaction API + UI
- `PUT /transactions/{transaction_id}`
- Sửa field quan trọng.
- Invalidate query frontend và refresh analytics.
- Acceptance:
  - Sửa xong dữ liệu hiển thị lại đúng.

### 3.8 Delete transaction API + UI
- `DELETE /transactions/{transaction_id}`
- Confirm modal trước khi xóa.
- Trigger refresh summary.
- Acceptance:
  - Xóa xong dashboard phản ánh đúng dữ liệu.

### 3.9 Transaction list API
- `GET /transactions`
- Filter theo:
  - date range
  - category
  - merchant optional
- Pagination.
- Acceptance:
  - List mở rộng được khi dataset tăng.

### 3.10 Transaction history page
- Tạo list page với table/card view cơ bản.
- Hỗ trợ filter và empty state.
- Acceptance:
  - User xem được lịch sử giao dịch gần đây và toàn bộ giao dịch.

### 3.11 Tests
- Backend integration CRUD tests.
- Unit tests category suggestion logic.
- E2E upload -> review -> save transaction.
- Acceptance:
  - End-to-end transaction flow được khóa bằng test.

## Exit criteria phase 3
- OCR draft review hoạt động.
- Manual entry hoạt động.
- Transaction CRUD ổn định và cập nhật được analytics.
