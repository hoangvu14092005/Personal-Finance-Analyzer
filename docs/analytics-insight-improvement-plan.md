# Kế hoạch cải thiện Phân tích chi tiêu & Insight

> Tài liệu khung (framework plan) — chốt phạm vi, tránh lệch hướng khi triển khai.
> Mọi mục đều bám nguyên tắc: **số liệu deterministic từ `transactions`/line items, VND-only, realtime, cách ly theo `user_id`, không bịa số**.

---

## 1. Mục tiêu

- Đưa các năng lực phân tích **đã có ở backend nhưng chưa lên UI** ra cho người dùng.
- Làm Insight bớt khô khan: thêm luật mới + tùy chọn LLM diễn giải (giữ số liệu chuẩn xác).
- Bổ sung vài chiều phân tích mới có giá trị quan sát hành vi chi tiêu.

Không nằm trong phạm vi: đổi nguồn sự thật tiền (vẫn là `transactions`), thêm đa tiền tệ, đổi pipeline OCR.

---

## 2. Hiện trạng (gap analysis)

### Backend đã có (13 endpoint `/api/v1/analytics/*`)
`overview`, `categories`, `trends`, `merchants`, `calendar`, `anomalies`, `budgets`,
`products`, `tax`, `receipts-stats`, `diagnostics`, `forecast`, `insight-feed`.

### Frontend trang Phân tích đang dùng
`categories`, `trends`, `merchants`, `anomalies`, `insight-feed`.

### Khoảng trống (backend xong, UI chưa có)
| Endpoint | Service | Frontend lib wrapper | UI |
|---|---|---|---|
| `/analytics/forecast` | `forecast.py` | ❌ chưa có | ❌ |
| `/analytics/diagnostics` | `diagnostics.py` | ❌ chưa có | ❌ |
| `/analytics/products` | `analytics.compute_product_breakdown` | ❌ chưa có | ❌ |
| `/analytics/tax` | `analytics.compute_vat_summary` | ❌ chưa có | ❌ |
| `/analytics/calendar` | `analytics.compute_calendar_days` | ✅ có (`getAnalyticsCalendar`) | ❌ chưa render ở trang analytics |
| `/analytics/receipts-stats` | `analytics.compute_receipt_stats` | ❌ chưa có | ❌ |

### Insight hiện tại (`insights.py`, deterministic)
4 luật: `insufficient_data`, `top_category`, `period_change` (±20% so kỳ trước), `budget_exceeded`.
Chưa có: dự báo vượt ngân sách, merchant mới, subscription, cuối tuần vs ngày thường, LLM narration.

---

## 3. Nguyên tắc thiết kế (ràng buộc xuyên suốt)

1. **Deterministic-first**: mọi con số tính từ SQL. LLM (nếu dùng) chỉ viết câu chữ, KHÔNG sinh số.
2. **VND-only**: không hiển thị/đổi tiền tệ khác.
3. **Realtime**: query trực tiếp DB, không cache số liệu (insight có thể cache row nhưng evidence luôn từ aggregate).
4. **User isolation**: mọi query filter `user_id` server-side.
5. **Fail-soft**: 1 khối lỗi không làm sập cả trang (mỗi card tự xử lý empty/error).
6. **Không phá vỡ hợp đồng API hiện có** (schema `extra="forbid"` — thêm field phải cập nhật cả schema + lib type).

---

## 4. NHÓM A — Tận dụng backend đã có (ưu tiên cao nhất)

> Đặc điểm chung: backend xong → chủ yếu thêm **lib wrapper + type** ở `frontend/web/lib/analytics-api.ts` và **UI card** ở `frontend/web/app/analytics/analytics-client.tsx`. Backend gần như không sửa.

### A1. Card "Dự báo cuối tháng" (forecast)
- **Mục tiêu**: hiện chi tiêu dự kiến cuối tháng theo run-rate + cảnh báo ngày dự kiến vượt ngân sách từng danh mục.
- **API**: `GET /analytics/forecast` (đã có). Response: `month{period_month, days_elapsed, days_in_month, spent_so_far, daily_run_rate, projected_total}`, `budgets[]{category_name, budget_amount, projected_spend, projected_percent, status, projected_exceed_date}`.
- **Frontend**:
  - Thêm type `AnalyticsForecastResponse` + `getAnalyticsForecast()` vào lib.
  - UI: card "Dự báo cuối tháng" — progress bar đã chi / dự kiến, badge trạng thái (`on_track`/`warning`/`exceeded`), list ngân sách có ngày dự kiến vượt.
- **Lưu ý**: forecast neo theo "tháng hiện tại" (không theo range preset). UI đặt ở khu vực riêng, không gắn bộ lọc range.
- **Acceptance**: tài khoản demo (có giao dịch tháng hiện tại) thấy số dự báo > đã chi; tài khoản không có giao dịch tháng này → trạng thái rỗng gọn gàng.

### A2. Khối "Vì sao chi tiêu thay đổi" (diagnostics)
- **Mục tiêu**: trả lời "tại sao kỳ này tốn hơn/ít hơn kỳ trước" — phân rã theo danh mục, kèm merchant đóng góp chính.
- **API**: `GET /analytics/diagnostics?range=...` (đã có). Response: `current_total`, `previous_total`, `delta_amount`, `delta_percent`, `drivers[]{category_name, delta_amount, delta_percent, direction, top_merchants[]}`.
- **Frontend**:
  - Type `AnalyticsDiagnosticsResponse` + `getAnalyticsDiagnostics()`.
  - UI: header tổng delta (tăng/giảm), list "driver" theo danh mục với mũi tên tăng/giảm + 1-2 merchant đóng góp chính.
- **Phụ thuộc range**: dùng chung bộ lọc range của trang.
- **Acceptance**: khi có dữ liệu cả 2 kỳ → hiện đúng top driver; thiếu kỳ trước → "chưa đủ dữ liệu so sánh".

### A3. Bảng "Top sản phẩm/món" (products)
- **Mục tiêu**: từ line item hóa đơn đã confirm — "bạn mua gì nhiều nhất", số lượng, tổng tiền, % đóng góp.
- **API**: `GET /analytics/products?range=...&limit=...` (đã có). Response: `items[]{item_name, total_amount, total_quantity, line_count, percentage}`.
- **Frontend**:
  - Type `AnalyticsProductsResponse` + `getAnalyticsProducts()`.
  - UI: bảng/list top sản phẩm với thanh % đóng góp.
- **Lưu ý**: chỉ tính line item của hóa đơn đã confirm → cần nhắc rõ "dựa trên hóa đơn OCR đã xác nhận" để tránh hiểu nhầm là toàn bộ chi tiêu.
- **Acceptance**: user có line item → hiện đúng top; user chưa có hóa đơn → empty state có hướng dẫn upload.

### A4. Khối "VAT & người bán" (tax)
- **Mục tiêu**: tổng tiền hàng trước thuế, tổng thuế, thuế suất hiệu dụng, top nhà cung cấp — phục vụ ai theo dõi hóa đơn đỏ.
- **API**: `GET /analytics/tax?range=...` (đã có). Response: `subtotal_before_tax`, `total_tax`, `grand_total`, `invoice_count`, `effective_tax_rate`, `top_sellers[]`.
- **Frontend**: type + `getAnalyticsTax()`; UI card 3 số tổng + list top seller (kèm MST).
- **Acceptance**: user có invoice → hiện số; không có → empty state.

### A5. (tùy chọn) Heatmap lịch chi tiêu (calendar)
- **Mục tiêu**: lịch nhiệt theo ngày, cường độ 0-4, đánh dấu ngày bất thường.
- **API**: `GET /analytics/calendar?range=90d` (đã có) + lib `getAnalyticsCalendar` (đã có).
- **Frontend**: chỉ cần component heatmap (grid theo tuần × thứ). Đây là phần nặng UI nhất nhóm A → tách riêng, làm sau A1-A4.

### Khối lượng nhóm A
Chủ yếu frontend. Mỗi mục A1-A4: ~1 wrapper + 1 card. Không migration, không đổi schema backend.

---

## 5. NHÓM B — Insight thông minh hơn

### B1. Thêm luật insight deterministic mới (trong `insights.py`)
Bổ sung vào `generate_rule_based_insights`, mỗi luật có `type` riêng + evidence từ aggregate:

| Type mới | Ý nghĩa | Nguồn dữ liệu |
|---|---|---|
| `budget_projected_exceed` | Dự báo SẼ vượt ngân sách (cảnh báo sớm, trước khi vượt thật) | `forecast.py` |
| `category_surge` | 1 danh mục tăng đột biến so kỳ trước | `diagnostics.py` |
| `new_merchant` | Merchant lần đầu xuất hiện trong kỳ | `transactions` (so với lịch sử) |
| `recurring_charge` | Giao dịch lặp đều (nghi subscription) | `transactions` group theo merchant + chu kỳ |
| `weekend_spike` | Chi cuối tuần cao bất thường so ngày thường | `transactions` group theo thứ |

- **Quy ước**: mỗi luật là 1 hàm nhỏ, cờ `wants(type_)` để bật/tắt; có ngưỡng rõ ràng (tránh nhiễu).
- **Acceptance**: mỗi luật có test deterministic (input cố định → insight cố định).

### B2. LLM diễn giải insight (tùy chọn, sau B1)
- **Mục tiêu**: giữ evidence số deterministic, LLM chỉ viết `title`/`summary` tự nhiên + gợi ý hành động.
- **Ràng buộc**:
  - Chỉ chạy khi user bật `allow_ai_data_processing`.
  - LLM nhận evidence đã tính sẵn, **cấm sinh số mới**; nếu LLM lỗi → fallback về text deterministic (fail-soft).
  - Không gọi LLM đồng bộ làm chậm feed: cân nhắc sinh khi tạo insight (cache row) thay vì mỗi request.
- **Acceptance**: tắt cờ → text như cũ; bật cờ + LLM lỗi → vẫn ra text cũ, không vỡ.

### B3. Insight actionable
- Mỗi insight kèm 1 action cụ thể (đã có cấu trúc `actions_json`): "Đặt ngân sách cho {danh mục}", "Xem giao dịch {merchant}", "Mở dự báo".
- Frontend render action thành nút điều hướng.

---

## 6. NHÓM C — Chiều phân tích mới (giá trị cao, chi phí lớn hơn)

### C1. So sánh cùng kỳ năm trước (YoY)
- Cần đủ dữ liệu lịch sử (>12 tháng). Thêm option so sánh "cùng kỳ năm ngoái" cạnh "kỳ trước".
- **Phụ thuộc**: mở rộng `previous_period`/diagnostics để nhận mốc so sánh YoY.

### C2. Chi cố định vs biến đổi
- Tách subscription/hóa đơn định kỳ (từ B1 `recurring_charge`) khỏi chi linh hoạt → 2 nhóm để người dùng biết "tiền cứng" mỗi tháng.

### C3. Heatmap nâng cao / drill-down
- Từ A5 mở rộng: click 1 ngày → xem giao dịch ngày đó.

> Nhóm C làm sau khi A + B ổn định; có thể tách spec riêng.

---

## 7. Lộ trình đề xuất

1. **Đợt 1 (Nhóm A lõi)**: A1 forecast → A2 diagnostics → A3 products → A4 tax. Thêm lib wrapper + card, không đụng backend.
2. **Đợt 2 (Nhóm B)**: B1 luật mới (deterministic + test) → B3 actionable → B2 LLM narration (tùy chọn).
3. **Đợt 3 (Nhóm A5 + Nhóm C)**: heatmap → YoY → cố định/biến đổi.

---

## 8. Rủi ro & lưu ý

- **Dữ liệu ngày tương lai**: hóa đơn test có `issue_date` ở tương lai sẽ nằm ngoài range mặc định → một số card rỗng dù có dữ liệu. Cân nhắc thêm note/empty-state rõ ràng (vấn đề đã biết, không phải bug).
- **Schema `extra="forbid"`**: thêm field response phải đồng bộ cả Pydantic schema + TS type, nếu không sẽ lỗi validate.
- **Hiệu năng**: diagnostics/forecast query 2 kỳ — giữ limit hợp lý; không N+1.
- **LLM (B2)**: chi phí + độ trễ; bắt buộc fail-soft và tôn trọng cờ quyền riêng tư.

---

## 9. Kế hoạch kiểm thử

- **Backend**: unit test cho mỗi luật insight mới (B1) với dữ liệu cố định; test endpoint forecast/diagnostics/products/tax đã có — bổ sung case empty + có dữ liệu.
- **Frontend**: e2e Playwright (mock `page.route`) cho mỗi card mới: trạng thái có dữ liệu, rỗng, lỗi.
- **Regression**: chạy lại bộ test hiện có (API + worker + e2e) đảm bảo 0 fail.

---

## 10. Câu hỏi cần chốt trước khi code

1. Đợt 1 làm đủ A1-A4 hay chọn lọc (vd chỉ forecast + diagnostics trước)?
2. Insight LLM (B2): làm ngay đợt 2 hay để sau (giữ deterministic trước)?
3. Heatmap (A5) và Nhóm C: tách spec riêng hay gộp vào đây?

---

## 11. Trạng thái triển khai (cập nhật)

Đã quyết định: **làm hết cả 3 nhóm**. Kết quả:

### Đợt 1 — Nhóm A (DONE)
- A1 Forecast: lib `getAnalyticsForecast` + card "Dự báo cuối tháng" (progress + ngày dự kiến vượt ngân sách).
- A2 Diagnostics: lib `getAnalyticsDiagnostics` + card "Vì sao chi tiêu thay đổi" (driver theo danh mục + merchant).
- A3 Products: lib `getAnalyticsProducts` + card "Top sản phẩm / món".
- A4 Tax: lib `getAnalyticsTax` + card "VAT & người bán".
- A5 Calendar: lib có sẵn + card "Lịch nhiệt chi tiêu" (heatmap tuần × thứ, cường độ 0-4).
- (receipts-stats: đã thêm lib wrapper `getAnalyticsReceiptsStats`, chưa render card — để dành.)

### Đợt 2 — Nhóm B (DONE)
- B1: 4 luật insight mới trong `insights.py` — `budget_projected_exceed`, `category_surge`, `new_merchant`, `weekend_spike` (deterministic, có ngưỡng). Thêm query helper `query_merchants_seen_before`, `query_weekday_weekend_totals`.
- B2: `insight_narrator.py` — LLM diễn giải `title`/`summary` từ evidence, fail-soft, gated bởi `allow_ai_data_processing`, bỏ qua trong môi trường test, chỉ chạy khi tạo row mới (cache narration).
- B3: nút hành động (actionable) ở trang Insights — điều hướng theo `actions` (open_transactions/open_budgets/open_analytics).

### Đợt 3 — Nhóm C (DONE)
- C1 YoY: thêm `year_ago_period` + tham số `compare=previous_period|year_ago` cho endpoint `/analytics/diagnostics`.
- C2 Cố định vs biến đổi: `recurring.py` + endpoint `/analytics/recurring` + card "Chi cố định vs biến đổi" (phát hiện merchant định kỳ theo số tháng xuất hiện).

### Kiểm thử
- Toàn bộ backend: **321 test pass, 0 fail**.
- Smoke 7 endpoint mới/đổi qua API live: tất cả 200 + JSON hợp lệ.
- Frontend: 0 lỗi type/diagnostics; trang analytics compile 200.

### Còn để dành (không bắt buộc)
- e2e Playwright cho từng card mới (mock route) — nên bổ sung khi rảnh.
- Card receipts-stats (đã có lib, chưa render).
- C3 heatmap drill-down (click ngày → xem giao dịch).
