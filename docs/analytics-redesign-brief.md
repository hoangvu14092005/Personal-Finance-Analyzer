# BI Redesign — Trang Phân tích chi tiêu (bản đã chốt phạm vi)

> Tài liệu này đã được chuẩn hóa theo quyết định ngày làm việc. Phần ngoài phạm vi
> được ghi rõ ở mục 2 để tránh lệch hướng. Nguyên tắc: **không đổi nguồn sự thật
> tiền (transactions), VND-only, realtime, user isolation, ưu tiên tiếng Việt.**

---

## 1. Vai trò của trang

Trang Phân tích chi tiêu là một dashboard BI cá nhân, giúp người dùng trả lời nhanh:

1. Tôi đã chi bao nhiêu trong kỳ này?
2. Tiền đang đi vào những nhóm nào?
3. Nhóm nào chi nhiều bất thường / gần vượt ngân sách?
4. Khoản chi nào cần kiểm tra lại?
5. Tôi nên điều chỉnh gì cho kỳ tiếp theo?

Mục tiêu redesign: rõ ràng, có phân cấp, màu sắc có ý nghĩa, insight hành động, và hệ danh mục tiếng Việt thống nhất.

---

## 2. Phạm vi đã chốt

### TRONG phạm vi (LÀM)
- **(1) Chuẩn hóa danh mục + can thiệp dữ liệu**: gộp bộ tiếng Anh cũ vào bộ tiếng Việt, thêm "Thực phẩm & siêu thị" → **15 danh mục tiếng Việt**, xóa hẳn category tiếng Anh cũ.
- **(5) Insight summary banner** bằng ngôn ngữ tự nhiên ở đầu trang.
- **Redesign IA + layout**: tách tab, KPI row, đưa cảnh báo/insight lên vùng dễ thấy.
- **Chart bằng recharts** (đã cài sẵn 3.8.1): trend, donut, bar ngang, budget progress, heatmap chuẩn hóa.
- **(7) Bảng màu chart theo danh mục**: chốt SAU khi danh mục đã khóa.
- **Polish**: 4 trạng thái mỗi card, responsive, a11y, tooltip/legend.

### NGOÀI phạm vi (KHÔNG làm — theo quyết định)
- (2) Tách "OCR / nhập tay" ở KPI — bỏ (tránh sửa logic khác).
- (3) Tab/card "Chất lượng dữ liệu" — bỏ.
- (4) VAT "có VAT hợp lệ / chưa có VAT" + callout chênh lệch — bỏ. (Vẫn giữ VAT summary đơn giản đang có.)
- (6) Chuẩn hóa tên sản phẩm (Title Case) — bỏ.
- (6) Đổi "Dự báo" thành "Tổng kết kỳ" khi kỳ kết thúc — bỏ.

---

## 3. Chuẩn hóa danh mục (phần nền — làm trước tiên)

### 3.1. Hiện trạng DB (đã audit)
DB đang có **23 category hệ thống**, lẫn 2 bộ trùng nghĩa:
- Bộ tiếng Việt (id 9,10,11,13,14,15,16,17,18,19,20,21,22,23) — có màu, là bộ chuẩn.
- Bộ tiếng Anh cũ còn sót (id 1-8, 12) — không màu, cần gộp + xóa.

### 3.2. Danh mục chuẩn cuối cùng (15, tiếng Việt)
| # | Tên hiển thị | Ghi chú |
|---|---|---|
| 1 | Ăn uống | nhà hàng, quán ăn, giao đồ ăn |
| 2 | Cà phê & đồ uống | cà phê, trà sữa, quán nước |
| 3 | **Thực phẩm & siêu thị** | **MỚI** — siêu thị, cửa hàng tiện lợi, hàng tiêu dùng thiết yếu |
| 4 | Mua sắm | thời trang, đồ gia dụng, bán lẻ không phải siêu thị |
| 5 | Di chuyển | taxi, xe công nghệ, xăng, gửi xe |
| 6 | Du lịch | khách sạn, vé máy bay, tour |
| 7 | Giáo dục | sách, văn phòng phẩm, học phí |
| 8 | Giải trí | rạp phim, game, streaming |
| 9 | Sức khỏe & y tế | nhà thuốc, khám bệnh |
| 10 | Hóa đơn & tiện ích | điện, nước, internet, điện thoại |
| 11 | Nhà ở | thuê nhà, sửa chữa, nội thất |
| 12 | Làm đẹp & chăm sóc cá nhân | spa, salon, mỹ phẩm |
| 13 | Chuyển khoản & rút tiền | ATM, chuyển khoản, phí ngân hàng |
| 14 | Quà tặng & quyên góp | quà tặng, từ thiện |
| 15 | Khác | chưa phân loại |

### 3.3. Bản đồ gộp tiếng Anh cũ → tiếng Việt (đã đối chiếu usage)
| ID cũ (xóa) | → ID Việt đích | Dữ liệu đang trỏ tới |
|---|---|---|
| 1 Food | 9 Ăn uống | tx:1, alias:2 |
| 2 Transport | 10 Di chuyển | tx:2, budget(user3) id=9, alias:2 |
| 3 Shopping | 11 Mua sắm | — |
| 4 Bills | 15 Hóa đơn & tiện ích | — |
| 5 Health | 16 Sức khỏe & y tế | — |
| 6 Education | 17 Giáo dục | — |
| 7 Entertainment | 13 Giải trí | tx:1, alias:1 |
| 8 Other | 23 Khác | — |
| 12 Hóa đơn | 15 Hóa đơn & tiện ích | tx:1, budget(user1) id=4 |

### 3.4. Kế hoạch can thiệp dữ liệu (FK-safe, kiểm tra ràng buộc)
Thực hiện trong 1 transaction:
1. Thêm category mới "Thực phẩm & siêu thị" (is_system, user_id=NULL, có màu).
2. Repoint `category_id` cũ → Việt ở các bảng: `transactions`, `receipt_line_items`, `budgets`, `user_merchant_aliases`.
3. Xóa 9 category tiếng Anh cũ (id 1-8, 12).

Ràng buộc đã kiểm tra (không vi phạm):
- `budgets` unique `(user_id, category_id, period_month)`:
  - user3 budget id=9 (cat 2→10, 2026-05): user3 chưa có budget cat 10 → an toàn.
  - user1 budget id=4 (cat 12→15, 2026-05): user1 chưa có budget cat 15 → an toàn.
- `user_merchant_aliases` unique `(user_id, raw_name)`: chỉ đổi `category_id`, không đổi raw_name → an toàn.

Cách triển khai: **migration Alembic mới** (thêm category + data fix + xóa cũ) để reproducible, kèm chạy trực tiếp trên DB dev hiện tại.

### 3.5. Cập nhật code đi kèm
- Migration seed cũ (`c8d9e0f1a2b3`) seed 14 → cần đảm bảo "Thực phẩm & siêu thị" có trong danh sách seed cho user mới/môi trường mới (idempotent).
- `category_classifier` / `category_suggestion`: bộ category truyền vào LLM tự lấy từ DB nên tự cập nhật; chỉ cần đảm bảo prompt mô tả phân biệt "Thực phẩm & siêu thị" vs "Mua sắm".

### 3.6. CÂU HỎI CẦN CHỐT (ảnh hưởng dữ liệu)
**Re-phân loại giao dịch siêu thị hiện có?** Các giao dịch ở merchant siêu thị (WinMart, Co.opmart, Bách Hóa Xanh, WinMart+...) hiện đang thuộc "Mua sắm". Khi thêm "Thực phẩm & siêu thị":
- (A) Re-phân loại các giao dịch/line item/alias siêu thị đang có sang danh mục mới (dữ liệu lịch sử nhất quán hơn), HOẶC
- (B) Chỉ áp dụng cho giao dịch mới từ giờ (không đụng dữ liệu cũ).

> Chưa chốt → mục 3.4 mặc định KHÔNG tự re-phân loại siêu thị, chờ xác nhận.

---

## 4. Cấu trúc thông tin (IA) — tab hóa

Trang chia thành 5 tab, mỗi tab một câu hỏi phân tích:

```
Tổng quan | Danh mục | Dòng tiền | Chứng từ & VAT | Gợi ý
```

(Nếu cần gọn có thể gộp còn 4 — sẽ chốt ở bước layout. PillTab đã có sẵn.)

Chung cho mọi tab: **header + bộ lọc range** (7d / 30d / Tháng này / Tháng trước / Tùy chỉnh) hiển thị kèm khoảng ngày cụ thể (vd "01/05/2026 – 31/05/2026").

### Tab 1 — Tổng quan
- **KPI row (5 thẻ)**: Tổng chi (+Δ kỳ trước) · Số giao dịch · Danh mục lớn nhất (+%) · Cảnh báo (số giao dịch cần kiểm tra) · Mức dùng ngân sách (%).
  - Lưu ý: KPI "Số giao dịch" KHÔNG tách OCR/nhập tay (ngoài phạm vi).
- **Insight summary banner** (mục 5): 1 đoạn ngôn ngữ tự nhiên tóm tắt kỳ.
- **Biểu đồ xu hướng** (bar theo ngày/tuần, có tooltip).
- **Giao dịch cần kiểm tra** (anomalies) — bảng có lý do + CTA (Xem hóa đơn / Sửa danh mục).
- **Vì sao chi tiêu thay đổi** (diagnostics) + **Ngân sách nhanh** (progress).

### Tab 2 — Danh mục
- Donut phân bổ (tâm donut = tổng chi) + danh sách danh mục (màu, số tiền, %, số giao dịch).
- Bar ngang so sánh số tiền giữa danh mục.
- Drill-down khi click danh mục: tổng, %, số giao dịch, người bán lớn nhất, sản phẩm nổi bật + CTA (Xem giao dịch / Đặt ngân sách / So sánh kỳ trước).

### Tab 3 — Dòng tiền
- Chi theo ngày/tuần (bar/area tùy range).
- Calendar heatmap (chuẩn hóa ô/khoảng cách) hoặc "Top ngày chi nhiều" khi màn nhỏ.
- Nhịp chi trung bình (VND/ngày) + dự báo cuối kỳ (giữ nguyên logic forecast hiện tại; KHÔNG đổi nhãn "Tổng kết kỳ").

### Tab 4 — Chứng từ & VAT
- VAT summary **đơn giản** (đang có): tổng trước thuế / thuế / tổng cộng / thuế suất hiệu dụng. KHÔNG thêm "VAT hợp lệ/chưa VAT" + callout.
- Người bán nổi bật (bar ngang, kèm MST).
- Top sản phẩm (ranked list) — KHÔNG chuẩn hóa tên (hiển thị như OCR trả về).
- KHÔNG có card "Chất lượng dữ liệu".

### Tab 5 — Gợi ý
- Danh sách insight ưu tiên (mỗi insight kèm CTA), thứ tự: vượt ngân sách → bất thường → gần vượt → danh mục chi nhiều → tiết kiệm → tham khảo.
- Gợi ý ngân sách kỳ sau (nếu có dữ liệu).

---

## 5. Insight summary banner (ngôn ngữ tự nhiên)

Đặt ngay dưới KPI ở tab Tổng quan. Một đoạn tóm tắt biến số liệu thành nhận định.

Ví dụ:
> Tháng này bạn đã chi 7.871.082 VND. Mua sắm là nhóm chi lớn nhất, chiếm 38,5%. Có 2 giao dịch lớn bất thường cần kiểm tra và 2 nhóm đang gần chạm ngân sách: Ăn uống, Cà phê & đồ uống.

Cách dựng (tận dụng hạ tầng đã có):
- Số liệu deterministic từ aggregate (tổng chi, danh mục lớn nhất, số bất thường, ngân sách gần vượt).
- Câu chữ: có thể dùng `insight_narrator` (LLM, fail-soft, gated `allow_ai_data_processing`) đã có; nếu tắt AI hoặc lỗi → ghép câu từ template deterministic.
- KHÔNG bịa số.

---

## 6. Biểu đồ (thay div tự vẽ bằng recharts)

| Khối | Loại recharts | Ghi chú |
|---|---|---|
| Xu hướng chi | BarChart (mặc định) / AreaChart | trục X dd/MM, tooltip VND, grid ngang mờ |
| Phân bổ danh mục | PieChart donut | màu theo category, tâm = tổng chi |
| So sánh danh mục / merchant / sản phẩm | BarChart layout vertical (thanh ngang) | so sánh số tiền chính xác |
| Ngân sách | progress bar / RadialBar | màu theo mức dùng |
| Lịch nhiệt | grid custom chuẩn hóa | ô 12px, gap 3px, 5 mức màu |

Chuẩn chung: `ResponsiveContainer` 100% width, chiều cao cố định; tooltip nền `surface-card` + viền `hairline`; font theo token; có `aria-label` mô tả.

---

## 7. Quy ước màu & trạng thái

### 7.1. Màu trạng thái (semantic)
| Ý nghĩa | Màu | Dùng cho |
|---|---|---|
| Dữ liệu chính / chi tiêu | xanh dương | tổng chi, trend |
| Tốt / trong kế hoạch | xanh lá | dư ngân sách, giảm chi |
| Cần chú ý | tím/cam nhẹ | gần vượt ngân sách |
| Rủi ro / bất thường | đỏ | bất thường, vượt ngân sách |
| Trung tính | xám | nhãn phụ, chưa đủ dữ liệu |

Quy ước: tăng = đỏ + mũi tên lên; giảm = xanh + mũi tên xuống. Màu KHÔNG phải kênh thông tin duy nhất — badge luôn có chữ (Cần chú ý / Vượt ngân sách / Bất thường / Ổn định).

### 7.2. Bảng màu chart theo 15 danh mục
**Chốt sau** khi danh mục đã khóa (mục 7 trong quyết định). Sẽ dùng nhất quán giữa donut, bar, legend, badge — ưu tiên tái dùng `color` đã seed trong DB cho từng category.

### 7.3. Bốn trạng thái mỗi card
- Loading: skeleton (không phải chữ "Đang tải").
- Empty: icon mờ + 1 câu + CTA (Đổi khoảng thời gian / Tải hóa đơn / Thêm giao dịch). Gợi ý "thử mở rộng khoảng thời gian" khi nghi do range.
- Error: viền đỏ nhạt + nút Thử lại.
- Data: nội dung chính.

---

## 8. Ngân sách & ngưỡng (hiển thị)
| Tỷ lệ dùng | Trạng thái | Màu |
|---|---|---|
| 0–70% | Đúng kế hoạch | xanh lá |
| 70–90% | Cần chú ý | tím/cam |
| 90–100% | Gần vượt | cam/đỏ nhẹ |
| >100% | Vượt ngân sách | đỏ |

(Khớp logic forecast/budget hiện có.)

---

## 9. Responsive & a11y
- Mobile 1 cột (KPI 2 cột), thứ tự: Tổng chi → Cảnh báo → Danh mục lớn nhất → trend đơn giản → top 3 insight → nút mở từng tab.
- `lg` 8/4; `xl` chi tiết hơn.
- Vùng chạm ≥ 40px; tooltip truy cập được bằng focus, không chỉ hover.
- Tương phản ≥ AA; không tuyên bố "đạt WCAG" (cần kiểm thử thủ công).

---

## 10. Lộ trình triển khai (đã rút gọn theo phạm vi)

- **Đợt 1 — Chuẩn hóa danh mục + data (backend/DB)**: migration thêm "Thực phẩm & siêu thị", gộp + xóa bộ tiếng Anh, cập nhật seed + classifier prompt. (Mục 3)
- **Đợt 2 — IA & layout (frontend)**: tab hóa, KPI row, insight summary banner. (Mục 4, 5)
- **Đợt 3 — Chart recharts**: trend, donut, bar ngang, budget progress, heatmap + bảng màu danh mục. (Mục 6, 7.2)
- **Đợt 4 — Polish**: 4 trạng thái, responsive, a11y, tooltip/legend. (Mục 7.3, 9)

Mỗi đợt xong sẽ báo để bạn duyệt trước khi sang đợt kế.

---

## 11. Tiêu chí nghiệm thu
- Danh mục 100% tiếng Việt, không còn tiếng Anh, không trùng nghĩa; dữ liệu cũ đã repoint đúng.
- Trang có phân cấp: KPI → insight summary → biểu đồ → chi tiết; chia tab rõ.
- Biểu đồ dùng recharts, có trục/tooltip/legend; heatmap chuẩn hóa.
- Mỗi insight/cảnh báo có CTA cụ thể.
- Mỗi card đủ 4 trạng thái; mobile không vỡ.
- 0 lỗi type; trang compile; test backend không regression.

---

## 12. Điều cần bạn chốt trước khi vào Đợt 1
1. **Re-phân loại giao dịch siêu thị hiện có** sang "Thực phẩm & siêu thị" (A) hay chỉ áp dụng giao dịch mới (B)? (mục 3.6)
2. **Số tab**: giữ **5 tab** hay gộp **4 tab**?
