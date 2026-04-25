# 1) Phạm vi sản phẩm

## 1.1 In scope cho MVP

MVP chỉ bao gồm các chức năng trực tiếp tạo giá trị cho việc nhập liệu nhanh, phân tích chi tiêu, và trả insight bằng AI.

### Chức năng chính

- Đăng ký, đăng nhập, đăng xuất.
- Quản lý hồ sơ người dùng cơ bản.
- Upload ảnh hóa đơn.
- OCR trích xuất dữ liệu từ hóa đơn.
- Tạo transaction draft từ OCR.
- Cho phép người dùng sửa transaction draft.
- Lưu giao dịch vào hệ thống.
- Dashboard tổng quan chi tiêu.
- Phân tích chi tiêu theo thời gian.
- Sinh insight và khuyến nghị bằng LLM.
- Thiết lập ngân sách đơn giản theo danh mục.
- Lọc giao dịch theo thời gian và danh mục.

---

## 1.2 Out of scope cho MVP

Các chức năng sau không triển khai ở MVP để tránh tăng độ phức tạp hệ thống:

- Đồng bộ tài khoản ngân hàng.
- Tự động đọc SMS banking.
- Quản lý đầu tư, chứng khoán, crypto.
- Quản lý nợ, khoản vay, trả góp phức tạp.
- Chatbot AI tự do theo kiểu hội thoại mở.
- Đồng bộ đa người dùng chung một tài khoản tài chính.
- Hỗ trợ kế toán doanh nghiệp/hộ kinh doanh.
- Dự báo dòng tiền dài hạn bằng mô hình ML riêng.
- OCR đa trang phức tạp cho hóa đơn dài hoặc sao kê ngân hàng.

---

# 2) Functional Requirements

## 2.1 Module Authentication

### FR-01: Đăng ký tài khoản

**Mô tả**

Người dùng có thể tạo tài khoản bằng email và mật khẩu.

**Input**

- Email
- Password
- Confirm password

**Output**

- Tài khoản được tạo thành công
- Điều hướng đến dashboard hoặc onboarding

**Validation**

- Email đúng định dạng
- Password đạt chính sách tối thiểu
- Email chưa tồn tại

**Acceptance Criteria**

- Nếu email hợp lệ và chưa tồn tại, hệ thống tạo tài khoản thành công.
- Nếu email đã tồn tại, hệ thống báo lỗi rõ ràng.
- Nếu password không hợp lệ, hệ thống không cho submit.

---

### FR-02: Đăng nhập

**Mô tả**

Người dùng đăng nhập bằng email/password.

**Acceptance Criteria**

- Đăng nhập thành công điều hướng vào app.
- Sai email hoặc mật khẩu hiển thị lỗi.
- Session được duy trì an toàn bằng token/cookie bảo mật.

---

### FR-03: Đăng xuất

**Acceptance Criteria**

- Khi đăng xuất, session hiện tại bị vô hiệu hóa.
- Người dùng bị chuyển về màn hình login.

---

## 2.2 Module Receipt Upload & OCR

### FR-04: Upload hóa đơn

**Mô tả**

Người dùng upload ảnh hóa đơn từ máy tính.

**Supported format**

- JPG
- PNG
- PDF 1 trang

**Business rule**

- Giới hạn kích thước file, ví dụ <= 10MB/file.
- Có thể upload 1 hoặc nhiều file trong một lần.

**Acceptance Criteria**

- Upload file hợp lệ thành công.
- File không hợp lệ bị từ chối với thông báo rõ ràng.
- Trạng thái xử lý hiển thị rõ: uploading, processing, completed, failed.

---

### FR-05: OCR trích xuất dữ liệu

**Mô tả**

Sau upload, hệ thống gửi file qua OCR service để trích xuất dữ liệu hóa đơn.

**Các trường ưu tiên**

- Merchant name
- Transaction date
- Total amount
- Currency
- Item list (nếu có)

**Business rule**

- OCR trả về confidence score cho từng trường nếu engine hỗ trợ.
- Nếu OCR thất bại, cho phép nhập tay.

**Acceptance Criteria**

- Hệ thống tạo được transaction draft từ kết quả OCR nếu có đủ dữ liệu tối thiểu.
- Nếu thiếu dữ liệu quan trọng, hệ thống gắn trạng thái “needs review”.
- Người dùng vẫn có thể lưu sau khi chỉnh sửa tay.

---

### FR-06: Xử lý lỗi OCR

**Mô tả**

Nếu OCR không đọc được, hệ thống không chặn luồng người dùng.

**Acceptance Criteria**

- Hiển thị thông báo OCR thất bại.
- Cho phép chuyển sang form nhập tay.
- Không làm mất file đã upload nếu cần retry.

---

## 2.3 Module Transaction Management

### FR-07: Tạo transaction draft

**Mô tả**

Sau OCR, hệ thống tạo một bản nháp giao dịch.

**Fields**

- Amount
- Date
- Merchant
- Category (suggested)
- Note
- Source = OCR/manual
- Confidence status

**Acceptance Criteria**

- Draft hiển thị cho người dùng trước khi lưu chính thức.
- Người dùng có thể sửa mọi trường quan trọng.

---

### FR-08: Phân loại giao dịch tự động

**Mô tả**

Hệ thống gợi ý danh mục chi tiêu dựa trên merchant, nội dung OCR, và lịch sử user.

**Danh mục top-level mẫu**

- Ăn uống
- Di chuyển
- Mua sắm
- Hóa đơn sinh hoạt
- Giải trí
- Sức khỏe
- Giáo dục
- Khác

**Acceptance Criteria**

- Mỗi transaction draft có 1 category mặc định hoặc “Uncategorized”.
- Người dùng có thể thay đổi category trước khi lưu.
- Lần chỉnh sửa của user được lưu để hỗ trợ gợi ý các lần sau.

---

### FR-09: Lưu giao dịch

**Mô tả**

Người dùng xác nhận draft để lưu thành transaction chính thức.

**Acceptance Criteria**

- Giao dịch được lưu thành công vào database.
- Dashboard cập nhật sau khi lưu.
- Event analytics được ghi lại.

---

### FR-10: Nhập giao dịch thủ công

**Mô tả**

Người dùng thêm giao dịch mà không cần OCR.

**Trường bắt buộc**

- Amount
- Date
- Category

**Trường tùy chọn**

- Merchant
- Note

**Acceptance Criteria**

- User có thể tạo giao dịch mới trong <= 1 form.
- Dữ liệu lưu thành công và hiển thị trên dashboard.

---

### FR-11: Chỉnh sửa giao dịch

**Mô tả**

Người dùng chỉnh sửa giao dịch đã lưu.

**Acceptance Criteria**

- Người dùng có thể sửa amount, date, merchant, category, note.
- Sau khi sửa, dashboard và summary liên quan được cập nhật.
- Có timestamp cập nhật cuối.

---

### FR-12: Xóa giao dịch

**Acceptance Criteria**

- Người dùng có thể xóa giao dịch.
- Sau khi xóa, tổng hợp dashboard thay đổi đúng.
- Có cơ chế confirm trước khi xóa.

## 2.4 Module Dashboard & Analytics

### FR-13: Dashboard tổng quan

**Mô tả**

Dashboard hiển thị tình hình tài chính ngắn gọn ngay khi người dùng vào app.

**Thành phần chính**

- Tổng chi trong kỳ
- Số lượng giao dịch
- Top danh mục chi tiêu
- Giao dịch gần đây
- Insight nổi bật

**Acceptance Criteria**

- Khi user có dữ liệu, dashboard render trong thời gian mục tiêu.
- Số liệu hiển thị đúng theo time filter đang chọn.

---

### FR-14: Lọc dữ liệu theo thời gian

**Options**

- 7 ngày gần nhất
- 30 ngày gần nhất
- Tháng này
- Tháng trước
- Custom range

**Acceptance Criteria**

- Thay đổi filter làm dashboard và insight cập nhật đúng.
- Không reload toàn trang.

---

### FR-15: Biểu đồ chi tiêu theo danh mục

**Acceptance Criteria**

- Có ít nhất 1 biểu đồ phân bổ chi tiêu theo category.
- Số liệu biểu đồ khớp với dữ liệu tổng.

---

### FR-16: Lịch sử giao dịch gần đây

**Acceptance Criteria**

- Hiển thị danh sách giao dịch mới nhất.
- Có phân trang hoặc lazy load nếu dữ liệu lớn.

---

## 2.5 Module Budget

### FR-17: Thiết lập ngân sách theo danh mục

**Mô tả**

Người dùng có thể đặt ngân sách hàng tháng cho từng danh mục.

**Acceptance Criteria**

- User tạo/sửa/xóa budget limit cho category.
- Dashboard hiển thị mức đã dùng so với ngân sách.
- Khi chi tiêu vượt ngưỡng, hệ thống gắn cảnh báo.

---

### FR-18: Cảnh báo vượt ngân sách

**Acceptance Criteria**

- Hệ thống hiển thị trạng thái cảnh báo khi actual spend > budget.
- Cảnh báo xuất hiện trên dashboard và trong AI summary nếu có.

---

## 2.6 Module AI Insights

### FR-19: Sinh insight tự động bằng LLM

**Mô tả**

Hệ thống dùng dữ liệu đã cấu trúc để tạo insight.

**Input cho LLM**

- Tổng chi theo thời gian
- Top category
- So sánh kỳ trước
- Xu hướng tăng/giảm
- Budget status

**Output**

- 3–5 insight ngắn
- 2–3 khuyến nghị hành động
- 0–2 cảnh báo nếu phát hiện bất thường

**Acceptance Criteria**

- Insight không được mâu thuẫn với dữ liệu nguồn.
- Nội dung phải cụ thể, không chung chung.
- Không đưa ra lời khuyên đầu tư hoặc tuyên bố rủi ro tài chính chuyên môn.

---

### FR-20: Làm mới insight theo kỳ lọc

**Acceptance Criteria**

- Khi người dùng đổi time range, hệ thống sinh lại insight tương ứng hoặc dùng cache.
- Nội dung insight phải bám theo filter hiện tại.

---

### FR-21: Giới hạn phạm vi AI

**Business rule**

- AI không trả lời câu hỏi mở ngoài domain chi tiêu cá nhân.
- AI không đưa ra nội dung suy đoán nếu dữ liệu không đủ.
- AI phải có fallback message khi thiếu dữ liệu.

**Acceptance Criteria**

- Với dữ liệu không đủ, hệ thống hiển thị thông báo kiểu: “Chưa đủ dữ liệu để tạo phân tích có ý nghĩa”.
- Không tạo insight bịa.

---

# 3) Non-functional Requirements

## 3.1 Hiệu năng

- Dashboard first load: <= 2 giây với dưới 1.000 giao dịch.
- OCR result preview: <= 8 giây cho ảnh chuẩn.
- Save transaction: <= 1 giây.
- AI summary: <= 5 giây sau khi summary data đã sẵn sàng.

## 3.2 Khả dụng

- Uptime hàng tháng >= 99.5%.
- Retry hợp lý cho OCR/LLM API.
- Hệ thống không mất dữ liệu khi lỗi một phần ở AI layer.

## 3.3 Bảo mật

- HTTPS 100%.
- JWT secure cookie hoặc session token an toàn.
- Mã hóa dữ liệu nhạy cảm ở trạng thái lưu trữ.
- Storage hóa đơn ở private bucket.
- Phân quyền dữ liệu tuyệt đối theo user_id.

## 3.4 Riêng tư dữ liệu

- Chỉ gửi dữ liệu tối thiểu cần thiết đến bên thứ ba.
- Có chính sách xóa dữ liệu.
- Log nội bộ không chứa dữ liệu nhạy cảm vượt mức cần thiết.

## 3.5 Khả năng mở rộng

- OCR service và AI insight service scale độc lập.
- Job queue xử lý file bất đồng bộ.
- Dashboard summary có cache hoặc pre-aggregation.

## 3.6 Khả năng quan sát hệ thống

- Có logging cho upload, OCR job, AI summary job, transaction save.
- Có metric cho latency, error rate, queue depth.
- Có alert khi OCR failure rate hoặc API timeout tăng đột biến.

---

# 4) User Stories & Acceptance Criteria

## Epic A: Nhập liệu chi tiêu nhanh

### US-01

Là một người dùng mới, tôi muốn upload ảnh hóa đơn để không phải nhập chi tiêu bằng tay.

**Acceptance Criteria**

- Có nút upload rõ ràng trên màn hình chính.
- Sau upload, tôi thấy trạng thái xử lý.
- Khi OCR xong, tôi thấy dữ liệu được điền sẵn.

---

### US-02

Là một người dùng bận rộn, tôi muốn sửa nhanh kết quả OCR trước khi lưu để đảm bảo dữ liệu đủ đúng mà không mất nhiều thời gian.

**Acceptance Criteria**

- Tôi có thể sửa amount, date, merchant, category ngay trên 1 form.
- Sau khi bấm lưu, tôi thấy giao dịch xuất hiện trong danh sách.

---

### US-03

Là một người dùng gặp ảnh hóa đơn lỗi, tôi muốn nhập tay khoản chi để không bị chặn luồng sử dụng.

**Acceptance Criteria**

- Nếu OCR lỗi, hệ thống đưa ra lựa chọn nhập tay.
- Tôi vẫn hoàn thành việc lưu giao dịch.

---

## Epic B: Theo dõi và hiểu chi tiêu

### US-04

Là một người muốn kiểm soát tài chính, tôi muốn xem tổng chi theo thời gian để biết mình đang tiêu bao nhiêu.

**Acceptance Criteria**

- Dashboard hiển thị tổng chi kỳ hiện tại.
- Tôi có thể đổi mốc thời gian và số liệu cập nhật đúng.

---

### US-05

Là một người có ngân sách, tôi muốn xem chi tiêu theo danh mục để biết nhóm nào đang vượt kiểm soát.

**Acceptance Criteria**

- Có biểu đồ hoặc danh sách top category.
- Số liệu hiển thị tỷ trọng hoặc tổng tiền theo category.

---

### US-06

Là một người dùng quan tâm đến xu hướng, tôi muốn so sánh kỳ hiện tại với kỳ trước để biết chi tiêu đang tăng hay giảm.

**Acceptance Criteria**

- Dashboard hiển thị chênh lệch so với kỳ trước.
- Sự thay đổi được tính đúng cùng loại khoảng thời gian.

---

## Epic C: Nhận phân tích AI có thể hành động

### US-07

Là một người dùng không giỏi đọc số liệu, tôi muốn hệ thống diễn giải dữ liệu chi tiêu bằng ngôn ngữ dễ hiểu.

**Acceptance Criteria**

- Hệ thống tạo ít nhất 3 insight ngắn.
- Insight bám theo dữ liệu thật.
- Insight không sử dụng câu quá chung chung.

---

### US-08

Là một người muốn cải thiện thói quen chi tiêu, tôi muốn nhận khuyến nghị cụ thể để có thể hành động ngay.

**Acceptance Criteria**

- Có ít nhất 2 khuyến nghị.
- Khuyến nghị gắn với category hoặc xu hướng cụ thể.
- Không chứa lời khuyên đầu tư.

---

### US-09

Là một người dùng có ngân sách, tôi muốn hệ thống cảnh báo khi gần hoặc vượt ngân sách.

**Acceptance Criteria**

- Khi chi tiêu vượt ngưỡng, dashboard hiển thị warning.
- AI summary nhắc đúng category đang vượt.

---

# 5) Business Rules

## BR-01

Mỗi giao dịch phải thuộc đúng 1 user.

## BR-02

Mỗi giao dịch chỉ có 1 category top-level tại một thời điểm.

## BR-03

Một transaction từ OCR chỉ trở thành transaction chính thức khi người dùng lưu hoặc hệ thống auto-save theo rule được bật.

## BR-04

Nếu OCR confidence thấp hơn ngưỡng cấu hình, transaction draft phải ở trạng thái “needs review”.

## BR-05

Nếu không có ngày giao dịch hợp lệ, hệ thống được phép gợi ý ngày upload nhưng phải cho người dùng sửa.

## BR-06

Nếu không xác định được merchant, hệ thống gán giá trị mặc định và đánh dấu cần xác nhận.

## BR-07

Insight AI chỉ được sinh từ dữ liệu đã chuẩn hóa, không sinh trực tiếp từ OCR text thô.

## BR-08

Nếu dữ liệu trong khoảng thời gian chọn dưới ngưỡng tối thiểu, AI summary không được sinh insight mạnh; phải trả fallback.

## BR-09

Ngân sách mặc định là theo chu kỳ tháng.

## BR-10

Việc xóa giao dịch phải cập nhật lại summary và dashboard liên quan.

---

# 6) Data Model sơ bộ

## 6.1 Entity: User

- user_id
- email
- password_hash
- created_at
- updated_at
- default_currency
- timezone

## 6.2 Entity: ReceiptUpload

- receipt_id
- user_id
- file_url
- file_type
- file_size
- upload_status
- ocr_status
- created_at

## 6.3 Entity: OcrResult

- ocr_result_id
- receipt_id
- raw_text
- merchant_extracted
- date_extracted
- amount_extracted
- currency_extracted
- item_lines_json
- confidence_json
- created_at

## 6.4 Entity: Transaction

- transaction_id
- user_id
- receipt_id nullable
- amount
- currency
- transaction_date
- merchant_name
- category_id
- note
- source_type (ocr/manual)
- review_status
- created_at
- updated_at

## 6.5 Entity: Category

- category_id
- category_name
- parent_category_id nullable
- is_active

## 6.6 Entity: Budget

- budget_id
- user_id
- category_id
- monthly_limit
- currency
- effective_from
- is_active

## 6.7 Entity: InsightSnapshot

- insight_id
- user_id
- time_range_type
- time_range_start
- time_range_end
- summary_input_json
- summary_output_json
- created_at

## 6.8 Entity: UserMerchantMapping

- mapping_id
- user_id
- normalized_merchant
- preferred_category_id
- usage_count
- updated_at

---

# 7) API Spec sơ bộ

## 7.1 Auth APIs

### POST /auth/register

Request:

- email
- password

Response:

- user profile
- auth token/session

### POST /auth/login

Request:

- email
- password

Response:

- auth token/session
- user profile

### POST /auth/logout

Response:

- success = true

---

## 7.2 Receipt & OCR APIs

### POST /receipts/upload

Request:

- multipart file

Response:

- receipt_id
- upload_status

### GET /receipts/{receipt_id}/status

Response:

- upload_status
- ocr_status
- draft_status

### GET /receipts/{receipt_id}/draft

Response:

- extracted fields
- confidence
- suggested category

---

## 7.3 Transaction APIs

### POST /transactions

Request:

- amount
- date
- merchant
- category_id
- note
- receipt_id optional
- source_type

Response:

- transaction_id

### PUT /transactions/{transaction_id}

Request:

- editable fields

Response:

- updated transaction

### DELETE /transactions/{transaction_id}

Response:

- success = true

### GET /transactions

Query params:

- start_date
- end_date
- category_id
- page
- page_size

Response:

- list
- total_count

---

## 7.4 Dashboard APIs

### GET /dashboard/summary

Query params:

- range_type
- start_date optional
- end_date optional

Response:

- total_spend
- transaction_count
- top_categories
- recent_transactions
- budget_status
- comparison_previous_period

---

## 7.5 Budget APIs

### POST /budgets

### PUT /budgets/{budget_id}

### DELETE /budgets/{budget_id}

### GET /budgets

---

## 7.6 AI Insight APIs

### POST /insights/generate

Request:

- range_type
- start_date optional
- end_date optional

Response:

- insights
- recommendations
- alerts

### GET /insights/latest

Response:

- latest summary by range

# 8) Kiến trúc logic mức cao

## 8.1 Thành phần chính

- **Frontend Web App**
- **Backend API**
- **Auth Service**
- **OCR Processing Service**
- **Transaction Service**
- **Analytics Summary Service**
- **AI Insight Service**
- **Relational Database**
- **Object Storage**
- **Queue/Job Worker**
- **Cache Layer**

---

## 8.2 Luồng kỹ thuật chính

1. User upload file.
2. Backend lưu file vào object storage.
3. Backend tạo OCR job.
4. OCR worker xử lý file, lưu kết quả OCR.
5. Parser chuẩn hóa thành transaction draft.
6. Frontend lấy draft và cho user review.
7. User xác nhận lưu transaction.
8. Transaction service ghi DB.
9. Analytics service cập nhật summary.
10. AI service dùng summary data để sinh insight.
11. Frontend hiển thị dashboard + insight.

---

## 8.3 Lý do kiến trúc này phù hợp

- Không chặn request web bởi OCR.
- Tách AI layer khỏi transaction layer để giảm rủi ro.
- Có thể scale OCR/AI theo tải riêng.
- Dễ cache dữ liệu dashboard và insight.

---

# 9) Rủi ro và phương án giảm thiểu

## Risk-01: OCR sai nhiều do chất lượng hóa đơn thấp

**Ảnh hưởng**

Làm transaction draft sai, user mất niềm tin.

**Mitigation**

- Hiển thị confidence.
- Cho phép sửa nhanh.
- Có fallback nhập tay.
- Áp dụng tiền xử lý ảnh cơ bản nếu cần.

---

## Risk-02: Chi phí LLM tăng nhanh

**Ảnh hưởng**

Không bền vững khi scale.

**Mitigation**

- Chỉ gửi dữ liệu tổng hợp.
- Cache insight theo kỳ.
- Không generate lại nếu dữ liệu không đổi.
- Giới hạn số lần refresh AI trong khoảng thời gian ngắn.

---

## Risk-03: Insight không hữu ích hoặc quá chung chung

**Ảnh hưởng**

Mất giá trị khác biệt của sản phẩm.

**Mitigation**

- Thiết kế prompt chặt.
- Đầu vào có schema rõ.
- Có rule-based checks sau khi LLM trả về.
- Thu thập feedback “useful / not useful”.

---

## Risk-04: Dashboard chậm khi số giao dịch tăng

**Mitigation**

- Pre-aggregate theo ngày/tháng.
- Cache summary.
- Pagination cho transaction list.

---

## Risk-05: Rủi ro riêng tư dữ liệu

**Mitigation**

- Tối thiểu hóa dữ liệu gửi sang bên thứ ba.
- Mã hóa storage.
- Kiểm soát retention.
- Audit log truy cập dữ liệu nhạy cảm.

---

# 10) Kế hoạch release đề xuất

## Phase 1 - MVP

- Auth
- Upload receipt
- OCR basic extraction
- Draft review
- Save transaction
- Dashboard summary
- Time filters
- Budget basic
- AI insights basic

## Phase 2

- Merchant learning tốt hơn
- Multi-upload tốt hơn
- OCR tối ưu hơn theo mẫu hóa đơn
- Insight history
- Export CSV/PDF

## Phase 3

- Kết nối nguồn dữ liệu khác
- Personalization sâu hơn
- Nâng cấp explainability cho AI
- Cảnh báo thông minh theo hành vi

---

# 11) Định nghĩa hoàn thành cho BA/Dev/UAT

## Done cho BA

- Có scope rõ ràng in/out.
- Có functional requirements và acceptance criteria.
- Có business rules.
- Có data model và API sơ bộ.
- Có KPI và success metrics.

## Done cho Dev

- Toàn bộ API cốt lõi triển khai xong.
- Pass unit test và integration test chính.
- Đạt performance threshold đã định.
- Không có lỗi blocker hoặc critical open.

## Done cho UAT

- Pass các luồng:
    - đăng nhập,
    - upload hóa đơn,
    - OCR draft review,
    - save transaction,
    - xem dashboard,
    - xem AI insight,
    - đặt ngân sách.
- Dữ liệu hiển thị đúng.
- Không có lỗi làm mất dữ liệu hoặc sai số tiền.