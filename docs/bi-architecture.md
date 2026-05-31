# Kiến trúc phân tích dữ liệu (BI) — Personal Finance Analyzer

Tài liệu này mô tả thiết kế tầng phân tích dữ liệu và ranh giới các giai đoạn,
để các phiên làm việc sau bám theo, tránh mơ hồ.

## Nguyên tắc nền tảng

1. **Real-time bằng query trực tiếp.** Mọi số liệu BI được tính trực tiếp từ DB
   ở mỗi request. KHÔNG có cache/snapshot. Dữ liệu mới hiện ngay ở lần load kế
   tiếp. Đây là lựa chọn có chủ đích cho dataset cá nhân (nhỏ).

2. **Nguồn sự thật tiền = transaction đã confirm.** Hóa đơn vừa OCR xong chưa
   vào BI tiền; chỉ khi user bấm confirm (tạo `transactions`) số liệu mới phản
   ánh. Đảm bảo số liệu không nhảy do OCR sai chưa kịp sửa (phương án A).

3. **VND-only.** Toàn hệ thống dùng VND. `transactions.currency` luôn được ép
   `"VND"` ở tầng service (create/update/confirm). `invoices.currency` giữ
   nguyên vì là dữ liệu chứng từ (chỉ hiển thị), không tham gia tổng hợp tiền.

## Luồng dữ liệu

```
                 ┌─────────────────────────────────────────────┐
                 │  Nguồn dữ liệu (DB, query trực tiếp)          │
                 │  - transactions        (tiền, đã confirm)     │
                 │  - receipt_line_items  (sản phẩm, đã confirm) │
                 │  - invoices            (VAT, đã confirm)      │
                 │  - receipt_uploads     (pipeline OCR)         │
                 └───────────────────────┬─────────────────────┘
                                         │
                          analytics_queries.py
                      (TẦNG TRUY VẤN BI HỢP NHẤT)
                      - query_period_totals
                      - query_category_aggregates
                      - query_merchant_aggregates
                      - query_product_aggregates
                      - query_vat_totals / query_seller_aggregates
                      - query_receipt_stats
                                         │
                          analytics.py (orchestration)
                      - compute_* : thêm %, format, gom nhóm
                                         │
                 ┌───────────────────────┼─────────────────────┐
                 │                        │                     │
          /analytics/* routes      insights.py            (G3) LLM/predictive
          /dashboard/summary    (rule-based insights)     tái dùng cùng nguồn
```

Điểm mấu chốt: **mọi truy vấn BI đi qua `analytics_queries.py`**. Các tầng trên
không tự viết SQL. Khi cần chiều phân tích mới, thêm hàm query ở tầng này rồi
gọi lên — số liệu nhất quán, dễ test, G3 tái dùng được.

## Các chiều phân tích hiện có

| Chiều | Nguồn | Endpoint |
|---|---|---|
| Tổng quan (tổng chi, delta kỳ trước) | transactions | `/analytics/overview`, `/dashboard/summary` |
| Theo danh mục | transactions | `/analytics/categories` |
| Theo cửa hàng | transactions | `/analytics/merchants` |
| Xu hướng theo thời gian | transactions | `/analytics/trends` |
| Lịch chi tiêu (heatmap) | transactions | `/analytics/calendar` |
| Giao dịch bất thường | transactions | `/analytics/anomalies` |
| Ngân sách | budgets + transactions | `/analytics/budgets` |
| **Theo sản phẩm/món** (G2) | receipt_line_items đã confirm | `/analytics/products` |
| **Thuế VAT + người bán** (G2) | invoices đã confirm | `/analytics/tax` |
| **Thống kê hóa đơn** (G2) | receipt_uploads | `/analytics/receipts-stats` |
| Insight feed (rule-based) | transactions + budgets | `/analytics/insight-feed`, `/insights` |
| **Diagnostic — phân rã nguyên nhân** (G3) | transactions (category + merchant) | `/analytics/diagnostics` |
| **Predictive — dự báo run-rate** (G3) | transactions + budgets | `/analytics/forecast` |

## Ranh giới 4 cấp độ phân tích

- **Descriptive ("đã xảy ra gì")** — ĐÃ HOÀN THIỆN. Toàn bộ bảng ở trên.
- **Diagnostic ("tại sao")** — ĐÃ CÓ (G3). `/analytics/diagnostics` phân rã thay
  đổi chi tiêu theo category, drill-down merchant đóng góp chính. (Cũ: chỉ có so
  kỳ trước + anomaly bằng luật.)
- **Predictive ("sắp tới thế nào")** — ĐÃ CÓ (G3, deterministic). `/analytics/forecast`
  dự báo chi cuối tháng theo run-rate + cảnh báo budget sắp vượt. KHÔNG dùng ML
  (dataset cá nhân nhỏ, cần giải thích được).
- **Conversational/RAG ("hỏi đáp tự nhiên")** — ĐÃ CÓ. Chatbot (Phase 6-7) với
  SQL tools + RAG vector. G3 bổ sung tool: products, VAT, diagnose, forecast.

## Chatbot tools (conversational layer)

Bot lấy dữ liệu qua 2 cơ chế: **SQL tools** (số liệu có cấu trúc) và **RAG tools**
(vector similarity trên text hóa đơn / embedding giao dịch). G3 mở rộng SQL tools:
- `get_product_breakdown`, `get_tax_summary` — khai thác dữ liệu G2.
- `diagnose_spending_change`, `forecast_month_spending` — gọi diagnostic/predictive.
- Các tool số liệu trùng (top_merchants, spending_by_day) đã refactor dùng chung
  `analytics_queries.py` để khớp dashboard (bảo toàn hành vi cũ qua flag).

## Quy ước khi mở rộng BI

1. Query mới → thêm hàm vào `analytics_queries.py` (trả dataclass thô, không %).
2. Logic hiển thị (%, format, gom nhóm) → đặt ở `analytics.py` (`compute_*`).
3. Endpoint → `app/api/v1/analytics.py`, response schema ở `schemas/analytics.py`.
4. Chiều dựa trên line-item/invoice phải lọc `transaction_id IS NOT NULL`
   (chỉ tính dữ liệu đã confirm) để khớp tinh thần real-time phương án A.
5. Mỗi chiều mới phải có test integration + verify trên Postgres thật.
