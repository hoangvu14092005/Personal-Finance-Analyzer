
## 1) Mục tiêu sản phẩm

### 1.1 Bài toán cần giải quyết

Người dùng cá nhân thường gặp ba vấn đề chính:

- Ghi chép chi tiêu không đều, dữ liệu rời rạc giữa hóa đơn, ảnh chụp và giao dịch nhập tay.
- Khó nhìn ra thói quen tài chính thực tế theo thời gian.
- Có dữ liệu nhưng không chuyển hóa được thành hành động cụ thể để cải thiện tình hình tài chính.

Sản phẩm này giải quyết bài toán bằng cách:

- Rút ngắn thời gian nhập dữ liệu chi tiêu nhờ OCR hóa đơn.
- Chuẩn hóa dữ liệu giao dịch thành cấu trúc có thể phân tích.
- Dùng LLM để diễn giải dữ liệu thành nhận xét, cảnh báo và khuyến nghị bằng ngôn ngữ tự nhiên.
- Tối ưu trải nghiệm web theo hướng nhanh, ít thao tác, phản hồi sớm.

### 1.2 Mục tiêu kinh doanh

- Tăng tần suất người dùng quay lại theo chu kỳ ngày/tuần để theo dõi tài chính.
- Tạo khác biệt bằng khả năng “hiểu dữ liệu và tư vấn” thay vì chỉ “ghi chép giao dịch”.
- Giảm chi phí vận hành bằng cách giới hạn AI vào các tác vụ có giá trị cao: OCR đầu vào và LLM đầu ra.

### 1.3 Mục tiêu sản phẩm đo được

- Giảm thời gian ghi nhận 1 hóa đơn xuống dưới 15 giây từ lúc upload đến khi lưu.
- Tăng tỷ lệ giao dịch được phân loại tự động lên mức đủ dùng cho dashboard và phân tích.
- Đảm bảo người dùng nhận được insight có thể hành động ngay trong phiên sử dụng đầu tiên.
- Duy trì tốc độ phản hồi cao trên web, ưu tiên trải nghiệm “xem nhanh kết quả” hơn số lượng tính năng.

### 1.4 Chỉ số giải quyết vấn đề người dùng

- Tỷ lệ hóa đơn được OCR thành công.
- Tỷ lệ giao dịch được gán danh mục tự động chính xác.
- Thời gian từ lúc người dùng mở web đến lúc thấy dashboard đầu tiên.
- Tỷ lệ người dùng nhận được ít nhất 1 insight và 1 khuyến nghị hữu ích trong phiên đầu tiên.
- Tỷ lệ chỉnh sửa thủ công sau OCR hoặc sau phân loại tự động.
- Tỷ lệ quay lại trong 7 ngày để xem phân tích mới.

---

## 2) Người dùng chính

Phân loại theo hành vi tài chính, không phân loại theo độ tuổi hay nghề nghiệp.

### 2.1 Nhóm 1: Người chi tiêu hàng ngày nhưng không theo dõi

**Đặc điểm hành vi**

- Có nhiều khoản chi nhỏ, phát sinh thường xuyên.
- Không ghi chép đều.
- Giữ hóa đơn hoặc ảnh chụp nhưng chưa tổng hợp.

**Nhu cầu**

- Nhập dữ liệu nhanh.
- Tự động gom nhóm chi tiêu.
- Xem ngay tổng chi và nhóm chi nổi bật.

**Giá trị sản phẩm**

- OCR giúp giảm nhập tay.
- Dashboard cho biết “tiền đang đi đâu”.
- LLM diễn giải xu hướng chi tiêu rõ ràng.

---

### 2.2 Nhóm 2: Người có ngân sách nhưng khó tuân thủ

**Đặc điểm hành vi**

- Có kế hoạch chi tiêu theo tháng.
- Biết các nhóm ngân sách chính nhưng khó kiểm soát vượt mức.
- Muốn có cảnh báo sớm thay vì chỉ xem báo cáo cuối tháng.

**Nhu cầu**

- Theo dõi chi tiêu theo danh mục.
- So sánh thực tế với ngân sách.
- Nhận cảnh báo vượt ngưỡng và gợi ý cắt giảm.

**Giá trị sản phẩm**

- Hệ thống theo dõi tiến độ ngân sách theo thời gian thực.
- LLM giải thích nguyên nhân vượt chi dựa trên lịch sử giao dịch.
- Gợi ý điều chỉnh khả thi theo từng danh mục.

---

### 2.3 Nhóm 3: Người muốn tối ưu tài chính cá nhân bằng dữ liệu

**Đặc điểm hành vi**

- Có ý thức quản lý tài chính.
- Muốn nhìn xu hướng theo tuần/tháng/quý.
- Quan tâm đến tỷ lệ tiết kiệm, chi tiêu bất thường, tính ổn định tài chính.

**Nhu cầu**

- Phân tích sâu hơn ở mức hành vi.
- Insight dạng xu hướng, so sánh kỳ trước, cảnh báo bất thường.
- Khuyến nghị có cơ sở từ dữ liệu cá nhân.

**Giá trị sản phẩm**

- Dashboard theo chu kỳ.
- Phát hiện biến động và mẫu lặp chi tiêu.
- LLM tạo báo cáo tóm tắt bằng văn bản dễ hiểu.

---

### 2.4 Nhóm 4: Người ít thời gian, ưu tiên tốc độ

**Đặc điểm hành vi**

- Không muốn thao tác nhiều.
- Chấp nhận mức chính xác “đủ tốt” nếu đổi lại tốc độ cao.
- Thường dùng app ngắn phiên, truy cập nhanh để xem số liệu.

**Nhu cầu**

- Upload nhanh, xử lý nhanh, xem nhanh.
- Giao diện tối giản.
- Hạn chế bước xác nhận và cấu hình.

**Giá trị sản phẩm**

- Luồng sử dụng ngắn.
- Ưu tiên auto-fill, auto-categorization.
- Phản hồi từng phần thay vì chờ hoàn tất toàn bộ.

---

## 3) Luồng sử dụng chính

### 3.1 Mục tiêu luồng

Đưa người dùng từ trạng thái “chưa có dữ liệu có cấu trúc” sang trạng thái “có dashboard và phân tích hành vi tài chính” trong một phiên ngắn.

### 3.2 Luồng chính end-to-end

### Bước 1: Mở web và đăng nhập

- Người dùng truy cập web app.
- Đăng nhập bằng email/password hoặc social login.
- Nếu là người dùng mới, hệ thống hiển thị onboarding ngắn:
    - mục đích app,
    - cách upload hóa đơn,
    - cách xem phân tích.

**Kết quả hệ thống**

- Tạo hồ sơ người dùng.
- Khởi tạo workspace tài chính cá nhân.
- Thiết lập đơn vị tiền tệ mặc định và múi giờ.

---

### Bước 2: Vào màn hình chính

- Người dùng nhìn thấy CTA chính: “Tải hóa đơn lên” hoặc “Thêm giao dịch”.
- Nếu chưa có dữ liệu, hiển thị empty state đơn giản, hướng dẫn 1 hành động đầu tiên.
- Nếu đã có dữ liệu, hiển thị dashboard tóm tắt:
    - tổng chi tháng này,
    - top danh mục chi,
    - số giao dịch mới,
    - insight nổi bật.

**Kết quả hệ thống**

- Tải dữ liệu tổng quan theo user.
- Render giao diện theo trạng thái có/không có dữ liệu.

---

### Bước 3: Upload hóa đơn hoặc ảnh chụp

- Người dùng kéo thả ảnh hoặc chọn file.
- Hỗ trợ ảnh đơn và nhiều ảnh, ưu tiên JPG/PNG/PDF 1 trang.
- Hệ thống hiển thị trạng thái upload và xử lý.

**Kết quả hệ thống**

- File được lưu tạm vào object storage.
- Tạo job OCR bất đồng bộ.
- Trả về trạng thái xử lý cho frontend.

---

### Bước 4: OCR trích xuất dữ liệu

OCR cần nhận diện tối thiểu các trường:

- tên cửa hàng hoặc đơn vị bán,
- ngày giao dịch,
- tổng tiền,
- danh sách món hàng nếu đọc được,
- loại tiền tệ nếu có.

**Kết quả hệ thống**

- OCR engine trích xuất text thô.
- Parser chuẩn hóa text thành transaction draft.
- Nếu độ tin cậy thấp, gắn cờ cần xác nhận.

**Yêu cầu tốc độ**

- Hiển thị kết quả sơ bộ sớm nhất có thể.
- Không chờ phân tích AI cấp cao mới cho người dùng thấy transaction draft.

---

### Bước 5: Chuẩn hóa và phân loại giao dịch

- Hệ thống tự động gán:
    - danh mục chi tiêu,
    - merchant chuẩn hóa,
    - tag gợi ý,
    - mức độ tin cậy.
- Người dùng có thể chỉnh sửa nhanh nếu cần.

**Kết quả hệ thống**

- Giao dịch được lưu vào cơ sở dữ liệu có cấu trúc.
- Mapping merchant-category được học lại ở mức rule-based hoặc preference-based cho user đó.
- Mọi chỉnh sửa thủ công được lưu để cải thiện lần sau.

---

### Bước 6: Cập nhật dashboard

Ngay sau khi giao dịch được lưu, dashboard cập nhật:

- tổng chi theo ngày/tháng,
- biểu đồ danh mục,
- lịch sử giao dịch gần nhất,
- chênh lệch so với kỳ trước.

**Kết quả hệ thống**

- Service phân tích tổng hợp dữ liệu theo user và time range.
- Cache dashboard summary để giảm thời gian tải lại.

---

### Bước 7: Sinh phân tích AI bằng LLM

LLM chỉ xử lý trên dữ liệu đã được cấu trúc, không xử lý trực tiếp ảnh gốc trong luồng chính.

Đầu vào cho LLM:

- tổng chi theo danh mục,
- xu hướng theo thời gian,
- biến động bất thường,
- tỷ lệ chi tiêu thiết yếu/không thiết yếu,
- ngân sách đã đặt nếu có.

Đầu ra mong muốn:

- 3 đến 5 insight ngắn, cụ thể, có căn cứ dữ liệu.
- 2 đến 3 khuyến nghị hành động.
- Cảnh báo nếu có dấu hiệu vượt ngân sách hoặc tăng chi bất thường.

Ví dụ loại insight:

- danh mục tăng mạnh nhất trong 30 ngày,
- merchant lặp lại với tần suất cao,
- ngày trong tuần có mức chi cao bất thường.

**Nguyên tắc**

- Không tạo lời khuyên tài chính đầu tư.
- Chỉ đưa ra gợi ý quản lý chi tiêu và thói quen cá nhân.
- Nội dung phải gắn với số liệu thực tế của user.

---

### Bước 8: Người dùng đọc kết quả và hành động

- Người dùng xem dashboard và AI summary.
- Có thể:
    - sửa giao dịch,
    - gắn ngân sách cho danh mục,
    - lọc theo khoảng thời gian,
    - xem lịch sử insight.

**Kết quả hệ thống**

- Ghi nhận event analytics.
- Lưu version insight theo chu kỳ để so sánh về sau.

---

### 3.3 Luồng phụ quan trọng

### Luồng nhập tay

Dùng khi:

- OCR thất bại,
- ảnh mờ,
- user muốn ghi nhanh một khoản chi không có hóa đơn.

Các trường tối thiểu:

- số tiền,
- ngày,
- danh mục,
- ghi chú tùy chọn.

### Luồng sửa sau OCR

- User mở transaction draft.
- Chỉnh lại merchant, date, amount hoặc category.
- Lưu và cập nhật dashboard ngay.

### Luồng xem phân tích theo kỳ

- Chọn 7 ngày, 30 ngày, tháng này, tháng trước.
- Xem sự thay đổi theo từng kỳ.
- Sinh lại insight tương ứng.

---

## 4) Giới hạn kỹ thuật

### 4.1 Giới hạn hạ tầng

Vì ưu tiên tinh gọn và tốc độ xử lý:

- Không nên dùng pipeline AI quá nặng trong giai đoạn đầu.
- OCR và LLM phải tách thành các service riêng để dễ scale.
- Luồng upload và parse phải bất đồng bộ để tránh chặn request web.

**Ràng buộc**

- Xử lý đồng thời số lượng lớn file ảnh có thể gây nghẽn CPU hoặc hàng đợi job.
- OCR trên ảnh kém chất lượng sẽ làm tăng thời gian xử lý và tỷ lệ sai.
- Nếu gọi LLM theo mỗi giao dịch riêng lẻ sẽ tốn chi phí và tăng latency; nên gom phân tích theo batch hoặc theo phiên.

---

### 4.2 Giới hạn về dữ liệu đầu vào

- Hóa đơn có thể không đồng nhất format.
- Ảnh có thể lệch góc, mờ, thiếu sáng, bị cắt.
- Một số hóa đơn không có đủ trường cần thiết.
- Merchant name có thể khó chuẩn hóa do OCR sai ký tự.

**Hệ quả kỹ thuật**

- Cần confidence score cho từng trường OCR.
- Cần fallback nhập tay.
- Cần rule xử lý dữ liệu thiếu, ví dụ:
    - thiếu ngày thì dùng ngày upload làm gợi ý,
    - thiếu merchant thì gắn “Unknown Merchant” và yêu cầu xác nhận.

---

### 4.3 Giới hạn bảo mật và quyền riêng tư

Dữ liệu tài chính cá nhân là dữ liệu nhạy cảm. Các yêu cầu tối thiểu:

- HTTPS toàn bộ.
- Mã hóa dữ liệu khi truyền và khi lưu.
- Phân quyền truy cập chặt theo user.
- Không để ảnh hóa đơn công khai.
- Không gửi dữ liệu thô không cần thiết sang bên thứ ba.

**Ràng buộc thực tế**

- Nếu dùng OCR API hoặc LLM API bên ngoài, cần kiểm soát:
    - dữ liệu nào được gửi ra ngoài,
    - thời gian lưu log phía nhà cung cấp,
    - điều khoản dùng dữ liệu để train model.
- Nên tách PII trước khi gửi vào prompt nếu không cần thiết.
- Cần retention policy cho ảnh gốc và bản OCR text.

---

### 4.4 Giới hạn API

### Với OCR API

- Có giới hạn kích thước file, tốc độ gọi, số request mỗi phút.
- Kết quả OCR có thể khác nhau theo ngôn ngữ và format hóa đơn.
- Cần retry logic và timeout rõ ràng.

### Với LLM API

- Có giới hạn token, tốc độ gọi, chi phí theo lượt phân tích.
- Prompt dài do lịch sử giao dịch lớn sẽ làm tăng chi phí và chậm phản hồi.
- Kết quả LLM có thể không ổn định nếu prompt không chuẩn hóa.

**Biện pháp kỹ thuật**

- Chỉ gửi dữ liệu tổng hợp, không gửi toàn bộ lịch sử thô nếu không cần.
- Dùng schema đầu ra cố định cho LLM.
- Cache kết quả insight theo time range.
- Đặt timeout riêng cho AI layer, không để treo UI.

---

### 4.5 Giới hạn hiệu năng frontend/backend

**Frontend**

- Không tải toàn bộ lịch sử giao dịch một lần.
- Dùng pagination hoặc lazy loading.
- Ưu tiên hiển thị dashboard summary trước.

**Backend**

- Cần tách read model và write model nếu tải tăng mạnh.
- Nên pre-compute summary theo ngày/tháng.
- Cần event queue cho OCR processing.

---

### 4.6 Giới hạn phạm vi sản phẩm giai đoạn đầu

Để giữ sản phẩm gọn:

- Không xử lý đầu tư, chứng khoán, tài sản phức tạp.
- Không đồng bộ ngân hàng tự động ở phiên bản đầu.
- Không hỗ trợ đa người dùng chung một ví ở giai đoạn đầu.
- Không làm chatbot AI mở hoàn toàn; chỉ làm insight và khuyến nghị dựa trên dữ liệu tài chính hiện có.

---

## 5) Tiêu chí hoàn thành

### 5.1 Tiêu chí chức năng

Sản phẩm đạt chuẩn MVP khi có đủ các khả năng sau:

- Đăng nhập và quản lý tài khoản.
- Upload ảnh hóa đơn.
- OCR trích xuất được các trường cơ bản.
- Tạo giao dịch từ kết quả OCR.
- Chỉnh sửa thủ công giao dịch.
- Dashboard tổng quan theo thời gian.
- AI summary tạo insight và khuyến nghị bằng văn bản.
- Lọc dữ liệu theo kỳ thời gian.

---

### 5.2 Tiêu chí định lượng về chất lượng xử lý

### OCR

- Tỷ lệ upload thành công: >= 98%.
- Tỷ lệ OCR trả về ít nhất 3 trường cốt lõi (ngày, tổng tiền, merchant): >= 85%.
- Độ chính xác trường tổng tiền trên tập dữ liệu kiểm thử chuẩn: >= 90%.
- Tỷ lệ giao dịch cần người dùng sửa nhiều hơn 2 trường: <= 20%.

### Phân loại giao dịch

- Tỷ lệ gán đúng danh mục top-level trên tập dữ liệu kiểm thử: >= 85%.
- Tỷ lệ người dùng chấp nhận danh mục tự động mà không sửa: >= 75%.

### Phân tích AI

- 100% insight phải dựa trên dữ liệu có thật trong hệ thống.
- Tỷ lệ insight bị đánh dấu “không hữu ích” bởi người dùng: <= 15%.
- Thời gian sinh AI summary sau khi dữ liệu đã sẵn sàng: <= 5 giây ở tải chuẩn.

---

### 5.3 Tiêu chí hiệu năng

- Thời gian load dashboard đầu tiên: <= 2 giây với user có dưới 1.000 giao dịch.
- Thời gian hiển thị kết quả OCR sơ bộ sau upload 1 ảnh chuẩn: <= 8 giây.
- Thời gian lưu giao dịch sau khi user xác nhận: <= 1 giây.
- Tỷ lệ request backend lỗi 5xx: < 1%.
- Uptime hệ thống hàng tháng: >= 99.5%.

---

### 5.4 Tiêu chí trải nghiệm người dùng

- Người dùng mới hoàn tất giao dịch đầu tiên trong <= 2 phút.
- Ít nhất 80% người dùng test có thể hoàn thành luồng upload hóa đơn mà không cần hướng dẫn trực tiếp.
- Tỷ lệ bỏ cuộc tại bước upload hoặc xác nhận OCR: <= 25%.
- Người dùng nhận được dashboard và ít nhất 1 insight trong phiên đầu tiên: >= 90%.

---

### 5.5 Tiêu chí bảo mật và tuân thủ

- 100% endpoint dùng HTTPS.
- 100% file hóa đơn lưu ở private storage.
- Có audit log cho các hành động nhạy cảm: đăng nhập, upload, xóa dữ liệu, export dữ liệu.
- Có cơ chế xóa dữ liệu người dùng theo yêu cầu.
- Không lưu raw prompt chứa dữ liệu nhạy cảm lâu hơn chính sách retention đã quy định.

---

### 5.6 Tiêu chí chấp nhận để release MVP

MVP được coi là đạt nếu đồng thời thỏa:

- Hoàn thành toàn bộ tính năng cốt lõi trong mục 5.1.
- Đạt tối thiểu 80% các chỉ số định lượng trong mục 5.2 và 5.3.
- Không có lỗi mức nghiêm trọng gây sai lệch số tiền hoặc lộ dữ liệu.
- Có thể phục vụ ổn định nhóm người dùng đầu tiên với tải nhỏ đến trung bình.

---

## Gợi ý phạm vi MVP đề xuất

Để đảm bảo tính khả thi kỹ thuật và đúng ưu tiên “tinh gọn, nhanh”, phạm vi MVP nên gồm:

- Đăng nhập
- Upload hóa đơn ảnh
- OCR trường cơ bản
- Sửa nhanh giao dịch
- Dashboard tổng chi và danh mục
- AI summary ngắn theo 7 ngày và 30 ngày
- Thiết lập ngân sách đơn giản theo danh mục

Chưa nên đưa vào MVP:

- Đồng bộ ngân hàng
- Chat AI tự do
- Dự báo tài chính dài hạn
- Phân tích đầu tư
- Hỗ trợ đa ví phức tạp

Tôi có thể tiếp tục chuyển spec này thành bản BRD/PRD chuẩn hơn với các mục như Functional Requirements, Non-functional Requirements, User Stories, Acceptance Criteria và API/Data Model.

[PRD / BA Spec mở rộng](https://www.notion.so/PRD-BA-Spec-m-r-ng-3224c23d639f80e5a87de5da302ddf7d?pvs=21)

[.](https://www.notion.so/3224c23d639f80ab9672dc45bfb70cc8?pvs=21)

[Code](https://www.notion.so/Code-33f4c23d639f80f39418f4184a97f3f3?pvs=21)