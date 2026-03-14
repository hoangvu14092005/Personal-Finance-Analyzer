# Phase 4 - Dashboard & Analytics

## Outcome
Dashboard hiển thị đúng dữ liệu chi tiêu, hỗ trợ filter theo thời gian và cập nhật mượt sau các thay đổi giao dịch.

## Task breakdown

### 4.1 Date range helpers
- Viết helper cho range:
  - 7d
  - 30d
  - this_month
  - last_month
  - custom
- Tính comparable previous period.
- Acceptance:
  - Logic range deterministic và có unit test.

### 4.2 Analytics service layer
- Tạo service tổng hợp:
  - total spend
  - transaction count
  - recent transactions
  - top categories
  - previous period delta
- Acceptance:
  - Summary trả đúng với fixture dataset.

### 4.3 Dashboard summary API
- `GET /dashboard/summary`
- Trả payload gọn cho frontend.
- Tối ưu query ở mức vừa đủ cho MVP.
- Acceptance:
  - Frontend không phải tự tính business logic.

### 4.4 Analytics refresh strategy
- Sau create/update/delete transaction:
  - invalidate cache hoặc
  - enqueue lightweight analytics refresh job
- Acceptance:
  - Dashboard không stale quá lâu sau mutation.

### 4.5 Frontend dashboard shell
- Tạo summary cards.
- Tạo recent transaction section.
- Tạo empty state khi chưa có dữ liệu.
- Acceptance:
  - Dashboard usable ngay cả khi account mới.

### 4.6 Time filter UX
- Dùng search params hoặc client state hợp lý.
- Fetch lại dữ liệu qua TanStack Query.
- Không full reload page.
- Acceptance:
  - Đổi filter mượt và sync với URL nếu cần.

### 4.7 Category chart
- Tạo chart data adapter.
- Render biểu đồ chi tiêu theo category.
- Acceptance:
  - Chart khớp với summary data.

### 4.8 Previous period comparison UI
- Hiển thị delta amount hoặc delta percent.
- Hiển thị label kỳ trước rõ ràng.
- Acceptance:
  - Không gây hiểu nhầm về mốc so sánh.

### 4.9 Loading, error, empty states
- Skeleton/loading state cho dashboard.
- Error banner/retry state.
- Acceptance:
  - UX rõ ràng khi API chậm hoặc lỗi.

### 4.10 Tests
- Unit tests cho date helpers và aggregation.
- Integration test dashboard summary API.
- E2E dashboard filter switching.
- Acceptance:
  - Dashboard logic được phủ test ở mức đủ dùng.

## Exit criteria phase 4
- Dashboard phản ánh đúng dữ liệu transaction.
- Filter theo thời gian mượt và chính xác.
- Có biểu đồ category và previous-period comparison.
