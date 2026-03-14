# Phase 6 - AI Insights

## Outcome
Hệ thống tạo insight bám dữ liệu thật, parse được theo schema chặt chẽ, có cache và fallback an toàn.

## Task breakdown

### 6.1 Summary input builder
- Tạo builder từ dữ liệu cấu trúc:
  - total spend
  - top categories
  - period comparison
  - budget status
  - anomaly candidates
- Acceptance:
  - Input builder deterministic và testable.

### 6.2 Eligibility rules
- Định nghĩa điều kiện đủ dữ liệu để generate insight.
- Ví dụ: cần đủ số transaction hoặc đủ dữ liệu ít nhất một range meaningful.
- Acceptance:
  - Hệ thống không tạo insight vô căn cứ.

### 6.3 Insight schemas
- Tạo Pydantic schema cho output:
  - insights[]
  - recommendations[]
  - alerts[]
- Tạo field constraints về độ dài và số lượng item.
- Acceptance:
  - Output parse được ổn định.

### 6.4 LLM provider abstraction
- Tạo interface provider cho AI insights.
- Implement:
  - `MockInsightProvider`
  - `OllamaInsightProvider`
  - `GeminiInsightProvider`
- Acceptance:
  - Có thể đổi provider bằng config.

### 6.5 Insight prompt builder
- Viết prompt chuyên cho domain chi tiêu cá nhân.
- Rule:
  - không bịa dữ liệu
  - không investment advice
  - không claim ngoài summary input
- Acceptance:
  - Prompt rõ và dễ kiểm soát.

### 6.6 TaskIQ insight job
- Tạo `generate_insight_job(user_id, range, fingerprint)`.
- Gọi provider.
- Parse output theo Pydantic.
- Lưu `InsightSnapshot`.
- Acceptance:
  - Insight generation chạy qua worker ổn định.

### 6.7 Caching strategy
- Cache theo `user_id + range + fingerprint(summary_input)`.
- Không regenerate nếu data chưa đổi.
- Acceptance:
  - Request lặp lại không tốn chi phí AI không cần thiết.

### 6.8 Grounding & safety checks
- Kiểm tra hậu xử lý:
  - không mâu thuẫn số liệu
  - không nhắc đến field không tồn tại
  - không advice bị cấm trong scope
- Acceptance:
  - Output đủ an toàn cho MVP.

### 6.9 Insight APIs
- `POST /insights/generate`
- `GET /insights/latest`
- Có response fallback khi chưa đủ điều kiện hoặc job chưa xong.
- Acceptance:
  - Frontend gọi được theo filter hiện tại.

### 6.10 Frontend insight UI
- Hiển thị card/list cho insight, recommendation, alert.
- Hiển thị state:
  - loading
  - ready
  - fallback
  - failed
- Acceptance:
  - UI gọn, rõ, không làm loãng dashboard.

### 6.11 Tests
- Unit tests input builder, eligibility, post-checks.
- Integration tests provider mock + caching.
- Golden tests cho schema parsing.
- Acceptance:
  - Insight pipeline đủ đáng tin cho MVP.

## Exit criteria phase 6
- Có AI insights dùng được với provider mock và ít nhất 1 provider thật.
- Có caching, fallback và hậu kiểm an toàn.
