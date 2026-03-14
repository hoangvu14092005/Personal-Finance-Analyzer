# Phase 5 - Budgets

## Outcome
User đặt budget theo category và nhìn thấy trạng thái sử dụng/nguy cơ vượt ngân sách trên dashboard.

## Task breakdown

### 5.1 Budget model & rules
- Hoàn thiện SQLModel `Budget`.
- Định nghĩa rule theo tháng hoặc period MVP.
- Validate limit > 0.
- Acceptance:
  - Không thể tạo budget dữ liệu vô nghĩa.

### 5.2 Budget CRUD APIs
- `POST /budgets`
- `PUT /budgets/{budget_id}`
- `DELETE /budgets/{budget_id}`
- `GET /budgets`
- Acceptance:
  - CRUD budget đầy đủ và đúng quyền truy cập theo user.

### 5.3 Budget usage calculation
- Tính spend thực tế theo category trong kỳ.
- Tính percent used.
- Gán trạng thái:
  - safe
  - warning
  - exceeded
- Acceptance:
  - Budget usage khớp transaction data.

### 5.4 Dashboard integration
- Đưa budget summary vào payload dashboard.
- Hiển thị used vs budget và trạng thái cảnh báo.
- Acceptance:
  - Dashboard hiển thị budget rõ và đúng.

### 5.5 Budget management UI
- Tạo form create/update/delete.
- Hiển thị danh sách budget theo category.
- Acceptance:
  - User thao tác budget thuận tiện.

### 5.6 Budget-specific filters and UX polish
- Sắp xếp budget theo mức sử dụng.
- Highlight category vượt ngưỡng.
- Acceptance:
  - User nhận ra budget risk ngay khi vào dashboard.

### 5.7 Tests
- Unit tests cho usage calculation.
- Integration tests cho CRUD + dashboard integration.
- Acceptance:
  - Budget logic không bị sai khi dữ liệu transaction đổi.

## Exit criteria phase 5
- Budget CRUD hoạt động end-to-end.
- Dashboard hiển thị đúng tình trạng used/warning/exceeded.
