# Personal Finance Analyzer — API Mapping Specification for 8 Core Screens v4

> Bản cập nhật này ưu tiên **API Mapping theo 8 màn UI** trước khi thiết kế database chi tiết.  
> Tài liệu này dùng để frontend, backend và database cùng bám một contract chung.

---

## 0. Trạng thái hiện tại

Giai đoạn hiện tại là:

```text
UI prototype / product design phase
```

Điều này có nghĩa:

```text
- Dữ liệu trên UI có thể là mock data.
- Backend chưa bắt buộc có đủ API thật.
- API trong tài liệu này là contract mục tiêu.
- Database chi tiết sẽ thiết kế sau khi API Mapping ổn định.
```

Không đánh giá UI theo việc backend đã có endpoint hay chưa. Chỉ cần kiểm tra:

```text
UI có đúng flow nghiệp vụ không?
Component có đủ data slot để map API không?
API contract có đúng source-of-truth không?
Database sau này có thể phục vụ API đó không?
```

---

# 1. Design order decision

## 1.1 Quyết định

Thứ tự thiết kế đúng cho sản phẩm này:

```text
1. Chốt domain/data model ở mức conceptual
2. Thiết kế API Mapping theo 8 màn
3. Từ API Mapping thiết kế database chi tiết
4. Kiểm tra chéo UI ↔ API ↔ DB
```

Không thiết kế database chi tiết quá sớm, vì dễ over-engineer và lệch UI flow.

---

## 1.2 Vì sao API Mapping nên đi trước database chi tiết?

Sản phẩm này có nhiều màn phụ thuộc cùng một dữ liệu:

```text
Overview
Analytics
Budget
Insights
Assistant
```

Tất cả đều cần đọc từ financial source-of-truth là `transactions`.

Nếu thiết kế database trước khi chốt màn hình cần gì, dễ xảy ra:

```text
- Tạo nhiều bảng chưa cần dùng.
- Thiếu field UI cần hiển thị.
- Nhầm receipt/OCR với transaction chính thức.
- Analytics tính từ nguồn sai.
- Chat trả lời không có evidence.
```

API Mapping theo màn giúp xác định:

```text
Màn nào cần dữ liệu gì?
Component nào cần field gì?
Action nào cần endpoint nào?
Endpoint đó đọc/ghi domain nào?
```

Sau đó database sẽ được thiết kế để phục vụ chính xác các API đó.

---

# 2. Conceptual domain model

Đây chưa phải database schema chi tiết. Đây là domain model nền để API Mapping không bị lệch logic.

## 2.1 Core entities

| Entity | Vai trò |
|---|---|
| `User` | Chủ sở hữu dữ liệu |
| `Transaction` | Dữ liệu tài chính chính thức |
| `ReceiptUpload` | File hóa đơn upload |
| `OcrResult` | Kết quả OCR raw + normalized |
| `ReceiptLineItem` | Dòng món hàng từ hóa đơn thường |
| `Invoice` | Hóa đơn điện tử / e-invoice |
| `InvoiceLineItem` | Dòng hàng hóa đơn điện tử |
| `Category` | Nhóm chi tiêu |
| `Budget` | Ngân sách theo category/tháng |
| `Merchant` | Merchant normalized toàn cục |
| `UserMerchantAlias` | Alias merchant theo user |
| `Insight` | Nhận xét/gợi ý có evidence |
| `ChatConversation` | Cuộc trò chuyện |
| `ChatMessage` | Tin nhắn chat |
| `Settings` | Cấu hình tài khoản/app |

---

## 2.2 Source-of-truth rules

```text
transactions = financial source of truth sau khi user xác nhận
receipts / OCR / invoices = document source, input, review, evidence, detail
budgets = target/limit
analytics = aggregate/read layer from transactions
insights = narrative/action layer based on evidence
assistant = conversation + tool orchestration
settings = user preferences affecting app behavior
```

## 2.3 Rule quan trọng nhất

Dashboard, Analytics, Budget usage, Insights tiền, Chat trả lời về tiền:

```text
Must read from transactions.
```

Receipt/OCR chưa confirm:

```text
Must not be counted as official financial data.
```

Sau khi user bấm:

```http
POST /api/v1/receipts/{receipt_id}/confirm
```

hệ thống tạo hoặc cập nhật đúng 1 `transaction` chính thức, liên kết về `receipt_upload_id`.

---

# 3. Global API standard

## 3.1 Base prefix

```http
/api/v1
```

## 3.2 Auth

```text
JWT HttpOnly cookie
current_user resolved server-side
client never sends user_id
```

## 3.3 Response envelope

### Single object

```json
{
  "data": {},
  "meta": {
    "request_id": "req_abc",
    "generated_at": "2026-05-28T10:30:00+07:00"
  }
}
```

### List

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "has_next": true
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

### Error

```json
{
  "error": {
    "code": "transaction.invalid_amount",
    "message": "Số tiền không hợp lệ.",
    "details": [],
    "request_id": "req_abc"
  }
}
```

## 3.4 Money/date conventions

```text
Money: decimal string, "5200000.00"
Currency: ISO string, "VND"
Date: YYYY-MM-DD
DateTime: ISO 8601 with timezone
```

## 3.5 Ownership rule

```text
Every endpoint uses current_user.
No endpoint accepts user_id from client.
Unowned resource returns 404.
```

---

# 4. Shared query standard

Các analytics endpoints dùng query chuẩn:

| Param | Type | Note |
|---|---|---|
| `range` | enum | `7d`, `30d`, `this_month`, `last_month`, `3m`, `6m`, `12m`, `custom` |
| `start_date` | date | Required if custom |
| `end_date` | date | Required if custom |
| `timezone` | string | Default user timezone |
| `currency` | string | Default user currency |
| `compare` | enum | `previous_period`, `same_period_last_month`, `none` |
| `category_id` | int | Optional |
| `merchant_id` | int | Optional |
| `include_pending` | bool | Default false |
| `limit` | int | Default 20 |
| `page` | int | Optional |
| `page_size` | int | Optional |
| `sort` | string | Optional |

---

# 5. Domain states

## 5.1 Receipt status

```text
uploaded
queued
processing
draft_ready
needs_review
ready
failed
deleted
```

## 5.2 OCR status

```text
pending
running
succeeded
failed
retrying
cancelled
```

## 5.3 Transaction status

```text
draft
needs_review
confirmed
corrected
deleted
```

## 5.4 Transaction source

```text
manual
ocr
import
system
```

## 5.5 Budget status

```text
safe
watch
warning
exceeded
no_budget
```

## 5.6 Insight severity

```text
info
success
watch
warning
danger
```

---

# 6. Screen 1 — Overview Dashboard

## 6.1 UI intent

Màn này trả lời nhanh:

```text
Tôi đã chi bao nhiêu?
So với kỳ trước tăng/giảm thế nào?
Danh mục nào chi nhiều nhất?
Ngân sách có ổn không?
Insight quan trọng nhất là gì?
```

## 6.2 Components → API mapping

| Component | API | Method | Data |
|---|---|---|---|
| KPI Cards | `/analytics/overview` | GET | total spent, daily average, transaction count, budget used |
| Spending Trend | `/analytics/trends` | GET | daily spend series |
| Category Breakdown | `/analytics/categories` | GET | category amount/percent |
| Budget Health Cards | `/analytics/budgets` | GET | budget usage |
| Hero Insight | `/analytics/insight-feed` | GET | top insight |
| Merchant Habits | `/analytics/merchants` | GET | frequent merchants |
| Recent Transactions | `/transactions` | GET | latest transactions |

## 6.3 Initial load

```http
GET /api/v1/analytics/overview?range=30d
GET /api/v1/analytics/trends?range=30d&group_by=day&compare=previous_period
GET /api/v1/analytics/categories?range=30d&limit=5
GET /api/v1/analytics/budgets?period_month=2026-05
GET /api/v1/analytics/insight-feed?range=30d&limit=1
GET /api/v1/analytics/merchants?range=30d&limit=5
GET /api/v1/transactions?limit=5&sort=-transaction_date
```

## 6.4 Main response examples

### GET /analytics/overview

```json
{
  "data": {
    "kpis": [
      {
        "key": "total_spent",
        "label": "Tổng chi",
        "value": "5200000.00",
        "format": "currency",
        "currency": "VND",
        "delta": {
          "value": "10.60",
          "format": "percent",
          "direction": "up",
          "tone": "warning",
          "label": "so với kỳ trước"
        }
      },
      {
        "key": "daily_average",
        "label": "Trung bình/ngày",
        "value": "185714.29",
        "format": "currency",
        "currency": "VND"
      },
      {
        "key": "transaction_count",
        "label": "Số giao dịch",
        "value": 42,
        "format": "number"
      },
      {
        "key": "budget_used",
        "label": "Ngân sách đã dùng",
        "value": "70.00",
        "format": "percent",
        "tone": "safe"
      }
    ],
    "data_freshness": {
      "last_transaction_at": "2026-05-28T09:15:00+07:00",
      "includes_pending_receipts": false
    }
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

## 6.5 Notes

- Không đọc OCR payload.
- Không đọc chat messages.
- Chỉ đọc `transactions` và `budgets`.

---

# 7. Screen 2 — Analytics Detail

## 7.1 UI intent

Màn phân tích sâu:

```text
Trend theo ngày/tuần/tháng
Category ranking
Merchant analysis
Calendar heatmap
Anomalies
Drill-down transactions
```

## 7.2 Components → API mapping

| Component | API | Method |
|---|---|---|
| Filter Options | `/categories`, `/analytics/merchants` | GET |
| Detailed Trend Chart | `/analytics/trends` | GET |
| Category Ranked Bars | `/analytics/categories` | GET |
| Merchant Analysis Table | `/analytics/merchants` | GET |
| Calendar Heatmap | `/analytics/calendar` | GET |
| Anomaly Cards | `/analytics/anomalies` | GET |
| Category Detail Snippet | `/transactions` | GET |
| Category Drilldown | `/analytics/categories/{category_id}` | GET |

## 7.3 Initial load

```http
GET /api/v1/categories
GET /api/v1/analytics/trends?range=30d&group_by=day&compare=previous_period
GET /api/v1/analytics/categories?range=30d
GET /api/v1/analytics/merchants?range=30d&limit=10
GET /api/v1/analytics/calendar?range=90d
GET /api/v1/analytics/anomalies?range=30d
```

## 7.4 Key endpoints

### GET /analytics/calendar

```json
{
  "data": {
    "days": [
      {
        "date": "2026-05-15",
        "amount": "620000.00",
        "transaction_count": 4,
        "intensity": 4,
        "top_category_name": "Mua sắm",
        "is_unusual": true
      }
    ],
    "legend": {
      "0": "no_spend",
      "1": "low",
      "2": "medium",
      "3": "high",
      "4": "unusual"
    }
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

### GET /analytics/anomalies

```json
{
  "data": {
    "anomalies": [
      {
        "id": "anom_123",
        "type": "large_transaction",
        "severity": "warning",
        "title": "Giao dịch lớn bất thường",
        "transaction_id": 123,
        "amount": "1250000.00",
        "baseline_amount": "450000.00",
        "reason": "Cao hơn trung bình 180%."
      }
    ]
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

---

# 8. Screen 3 — Upload Hóa Đơn

## 8.1 UI intent

User upload hóa đơn, hệ thống tạo receipt và OCR job.

```text
Upload file
→ create receipt
→ enqueue OCR
→ poll status
→ draft ready
```

## 8.2 Components → API mapping

| Component | API | Method |
|---|---|---|
| Upload Dropzone | `/receipts` | POST |
| Processing Timeline | `/receipts/{receipt_id}` | GET polling |
| Recent Uploads | `/receipts` | GET |
| Retry OCR | `/receipts/{receipt_id}/retry` | POST |
| Review CTA | `/receipts/{receipt_id}/draft` | GET |

## 8.3 Upload endpoint

```http
POST /api/v1/receipts
Content-Type: multipart/form-data
```

Form fields:

```text
file: binary
source: upload
client_timezone: Asia/Ho_Chi_Minh
```

Response:

```json
{
  "data": {
    "receipt_id": 123,
    "status": "queued",
    "ocr_status": "pending",
    "job_id": "job_abc",
    "filename": "highlands-receipt.jpg",
    "file_size": 1800000,
    "mime_type": "image/jpeg",
    "created_at": "2026-05-28T10:30:00+07:00"
  },
  "links": {
    "self": "/api/v1/receipts/123",
    "draft": "/api/v1/receipts/123/draft",
    "review": "/app/receipts/123/review"
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

## 8.4 Poll status

```http
GET /api/v1/receipts/123
```

Response:

```json
{
  "data": {
    "receipt_id": 123,
    "status": "processing",
    "ocr_status": "running",
    "progress": 68,
    "error_code": null,
    "updated_at": "2026-05-28T10:31:00+07:00"
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

## 8.5 Recent receipts

```http
GET /api/v1/receipts?limit=5&sort=-created_at
```

## 8.6 Receipt retrieval layer

Receipt retrieval phục vụ xem lại chứng từ, không phục vụ tính tổng tiền chính thức.

```http
GET /api/v1/receipts?receipt_date=2026-05-28
GET /api/v1/receipts?created_date=2026-05-28
GET /api/v1/receipts/{receipt_id}/image
GET /api/v1/receipts/{receipt_id}/line-items
GET /api/v1/receipts/{receipt_id}/transaction
GET /api/v1/transactions/{transaction_id}/receipt
GET /api/v1/receipts/{receipt_id}/invoice
GET /api/v1/invoices/{invoice_id}
GET /api/v1/invoices/{invoice_id}/line-items
```

Date semantics:

| Field | Meaning | Used for |
|---|---|---|
| `created_at` | Ngày user upload hóa đơn | “hóa đơn tôi upload hôm qua” |
| `receipt_date` | Ngày ghi trên hóa đơn/OCR đọc được | “hóa đơn ngày hôm qua” |
| `transaction_date` | Ngày giao dịch chính thức | “hôm qua tôi tiêu bao nhiêu” |
| `confirmed_at` | Ngày user xác nhận thành transaction | audit/review |

---

# 9. Screen 4 — OCR Review / Transactions

## 9.1 UI intent

Màn này có hai vai trò:

```text
1. Review OCR draft từ hóa đơn.
2. Quản lý transaction đã lưu.
```

Quan trọng:

```text
Receipt draft chưa phải transaction chính thức.
Confirm tạo hoặc cập nhật đúng 1 transaction chính thức và giữ receipt/invoice làm chứng từ đối chiếu.
```

## 9.2 Components → API mapping

| Component | API | Method |
|---|---|---|
| Receipt Detail | `/receipts/{receipt_id}` | GET |
| OCR Result | `/receipts/{receipt_id}/ocr-result` | GET |
| Draft/Review Form | `/receipts/{receipt_id}/draft` | GET |
| Save Review Edits | `/receipts/{receipt_id}/draft` | PATCH |
| Confirm Review | `/receipts/{receipt_id}/confirm` | POST |
| Receipt Line Items | `/receipts/{receipt_id}/line-items` | GET |
| Linked Transaction | `/receipts/{receipt_id}/transaction` | GET |
| Open Receipt From Transaction | `/transactions/{transaction_id}/receipt` | GET |
| Retry OCR | `/receipts/{receipt_id}/retry` | POST |
| Category Picker | `/categories` | GET |
| Merchant Suggestion | `/merchants/search` | GET |
| Transaction Table | `/transactions` | GET |
| Add Transaction | `/transactions` | POST |
| Edit Transaction | `/transactions/{transaction_id}` | PATCH |
| Delete Transaction | `/transactions/{transaction_id}` | DELETE |

## 9.3 Draft endpoint

```http
GET /api/v1/receipts/123/draft
```

Response:

```json
{
  "data": {
    "receipt_id": 123,
    "linked_transaction": null,
    "draft_status": "needs_review",
    "source": "ocr",
    "merchant": {
      "raw_name": "Highlands Coffee",
      "merchant_id": 10,
      "display_name": "Highlands Coffee",
      "normalized_name": "highlands coffee",
      "match_confidence": "96.00"
    },
    "transaction_date": "2026-05-18",
    "amount": "68000.00",
    "currency": "VND",
    "category": {
      "category_id": 1,
      "category_name": "Ăn uống"
    },
    "note": null,
    "line_items": [
      {
        "name": "Cà phê sữa đá",
        "quantity": "1",
        "unit_price": "39000.00",
        "total_amount": "39000.00"
      }
    ],
    "confidence": {
      "overall": "72.00",
      "merchant_name": "95.00",
      "transaction_date": "98.00",
      "amount": "72.00",
      "category": "90.00"
    },
    "warnings": [
      {
        "field": "amount",
        "code": "low_confidence",
        "message": "Tổng tiền có độ tin cậy thấp, vui lòng kiểm tra."
      }
    ]
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

## 9.4 Confirm review

```http
POST /api/v1/receipts/123/confirm
```

Request:

```json
{
  "merchant_name": "Highlands Coffee",
  "merchant_id": 10,
  "transaction_date": "2026-05-18",
  "amount": "68000.00",
  "currency": "VND",
  "category_id": 1,
  "note": "Cà phê sáng",
  "save_merchant_alias": true
}
```

Response:

```json
{
  "data": {
    "receipt_id": 123,
    "receipt_status": "ready",
    "transaction": {
      "transaction_id": 789,
      "merchant_name": "Highlands Coffee",
      "amount": "68000.00",
      "currency": "VND",
      "transaction_date": "2026-05-18",
      "category_id": 1,
      "category_name": "Ăn uống",
      "source": "ocr",
      "status": "confirmed"
    }
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

## 9.5 Transaction CRUD

```http
GET    /api/v1/transactions
POST   /api/v1/transactions
GET    /api/v1/transactions/{transaction_id}
PATCH  /api/v1/transactions/{transaction_id}
DELETE /api/v1/transactions/{transaction_id}
```

Transaction list response:

```json
{
  "data": [
    {
      "transaction_id": 789,
      "merchant": {
        "merchant_id": 10,
        "name": "Highlands Coffee",
        "normalized_name": "highlands coffee"
      },
      "category": {
        "category_id": 1,
        "name": "Ăn uống",
        "icon": "utensils"
      },
      "amount": "68000.00",
      "currency": "VND",
      "transaction_date": "2026-05-18",
      "source": "ocr",
      "status": "confirmed",
      "note": "Cà phê sáng",
      "receipt_upload_id": 123,
      "has_invoice": false
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 42,
    "has_next": true
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

---

# 10. Screen 5 — Budget Management

## 10.1 UI intent

Màn ngân sách trả lời:

```text
Tổng ngân sách bao nhiêu?
Đã dùng bao nhiêu?
Danh mục nào vượt?
Dự kiến cuối tháng ra sao?
```

## 10.2 Components → API mapping

| Component | API | Method |
|---|---|---|
| Budget Summary | `/analytics/budgets` | GET |
| Budget List | `/budgets` | GET |
| Create Budget | `/budgets` | POST |
| Edit Budget | `/budgets/{budget_id}` | PATCH |
| Delete Budget | `/budgets/{budget_id}` | DELETE |
| Budget History | `/budget-adjustments` | GET |
| Budget Recommendations | `/analytics/insight-feed` | GET |

## 10.3 Budget analytics

```http
GET /api/v1/analytics/budgets?period_month=2026-05
```

Response:

```json
{
  "data": {
    "period_month": "2026-05",
    "summary": {
      "total_budget": "15000000.00",
      "total_spent_in_budgeted_categories": "9750000.00",
      "overall_percent_used": "65.00",
      "remaining_amount": "5250000.00",
      "exceeded_count": 2,
      "warning_count": 1
    },
    "budgets": [
      {
        "budget_id": 1,
        "category_id": 1,
        "category_name": "Ăn uống",
        "budget_amount": "3000000.00",
        "spent_amount": "2100000.00",
        "remaining_amount": "900000.00",
        "percent_used": "70.00",
        "expected_percent_by_today": "90.32",
        "pace_status": "under_pace",
        "projected_month_end_spend": "2325000.00",
        "status": "safe"
      }
    ]
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

## 10.4 Budget CRUD

```http
GET    /api/v1/budgets?period_month=2026-05
POST   /api/v1/budgets
PATCH  /api/v1/budgets/{budget_id}
DELETE /api/v1/budgets/{budget_id}
```

Create request:

```json
{
  "category_id": 1,
  "period_month": "2026-05",
  "amount": "3000000.00",
  "currency": "VND"
}
```

---

# 11. Screen 6 — AI Insights

## 11.1 UI intent

Insights là nơi hệ thống chủ động đưa ra nhận xét có evidence.

```text
Insights = system-initiated recommendations
Assistant = user-initiated Q&A
```

## 11.2 Components → API mapping

| Component | API | Method |
|---|---|---|
| Hero Summary | `/analytics/insight-feed` | GET |
| Insight Card Grid | `/analytics/insight-feed` | GET |
| Insight Timeline | `/insights` | GET |
| Insight Detail | `/insights/{insight_id}` | GET |
| Generate Insight | `/insights/generate` | POST |
| Dismiss Insight | `/insights/{insight_id}` | PATCH |
| Insight Feedback | `/insights/{insight_id}/feedback` | POST |

## 11.3 Insight feed

```http
GET /api/v1/analytics/insight-feed?range=30d&limit=6
```

Response:

```json
{
  "data": {
    "hero": {
      "id": 100,
      "type": "category_increase",
      "severity": "warning",
      "title": "Ăn uống tăng 23.5% so với kỳ trước",
      "summary": "Bạn đã chi nhiều hơn cho ăn uống. Hãy xem chi tiết để tối ưu chi tiêu.",
      "evidence": [
        {
          "label": "Kỳ này",
          "value": "2100000.00",
          "format": "currency",
          "source_type": "transactions"
        }
      ],
      "actions": [
        {
          "type": "open_category",
          "label": "Xem chi tiết insight",
          "params": {
            "category_id": 1
          }
        }
      ]
    },
    "insights": []
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

## 11.4 Generate insight

```http
POST /api/v1/insights/generate
```

Request:

```json
{
  "range": "30d",
  "force_refresh": false,
  "types": ["category_increase", "budget_warning", "anomaly"]
}
```

---

# 12. Screen 7 — Financial Assistant Chat

## 12.1 UI intent

Màn Chat phải là **chat-first interface**, không phải dashboard phụ.

```text
Chat area rộng
History mở bằng drawer
Quick prompts nằm ngang
Context panel nhỏ/collapsible
Evidence inline
Actions compact
```

## 12.2 Layout decision

```text
App sidebar: 240px
Chat area: 70–75%
Context panel: 25–30%, collapsible
Conversation history: drawer
Quick prompts: horizontal bar
Composer: full width inside chat area
```

## 12.3 Components → API mapping

| Component | API | Method |
|---|---|---|
| Conversation Drawer | `/chat/conversations` | GET |
| New Conversation | `/chat/conversations` | POST |
| Message Thread | `/chat/conversations/{conversation_id}/messages` | GET |
| Send Message | `/chat/messages` | POST |
| Async Result | `/chat/messages/{message_id}/result` | GET |
| Feedback | `/chat/messages/{message_id}/feedback` | POST |
| Regenerate | `/chat/messages/{message_id}/regenerate` | POST |
| Delete Conversation | `/chat/conversations/{conversation_id}` | DELETE |
| Related Transactions | `/transactions` | GET on demand |
| Related Insights | `/analytics/insight-feed` | GET on demand |

## 12.4 Send message

```http
POST /api/v1/chat/messages
```

Request:

```json
{
  "conversation_id": 1,
  "message": "Tháng này tôi tiêu nhiều nhất vào đâu?",
  "context": {
    "range": "30d",
    "currency": "VND",
    "timezone": "Asia/Ho_Chi_Minh",
    "include_pending": false
  }
}
```

Response:

```json
{
  "data": {
    "conversation_id": 1,
    "user_message": {
      "message_id": 101,
      "role": "user",
      "content": "Tháng này tôi tiêu nhiều nhất vào đâu?",
      "created_at": "2026-05-28T10:28:00+07:00"
    },
    "assistant_message": {
      "message_id": 102,
      "role": "assistant",
      "content": "Bạn chi nhiều nhất vào Ăn uống với 2.1M ₫, chiếm 40.4% tổng chi trong 30 ngày qua.",
      "display": {
        "layout": "compact_answer",
        "answer_type": "category_breakdown"
      },
      "summary_metrics": [
        {
          "label": "Ăn uống",
          "value": "2100000.00",
          "format": "currency",
          "percent": "40.40",
          "rank": 1
        }
      ],
      "evidence": [
        {
          "source_type": "transactions",
          "label": "42 giao dịch đã xác nhận",
          "range": "30d"
        }
      ],
      "actions": [
        {
          "type": "open_transactions",
          "label": "Xem giao dịch",
          "params": {
            "category_id": 1,
            "range": "30d"
          }
        },
        {
          "type": "open_analytics",
          "label": "Xem phân tích",
          "params": {
            "category_id": 1,
            "range": "30d"
          }
        }
      ],
      "context_summary": {
        "range_label": "30 ngày",
        "data_sources": ["transactions"],
        "confirmed_transaction_count": 42,
        "includes_pending_receipts": false
      },
      "related": {
        "transactions_count": 18,
        "insights_count": 2,
        "load_on_demand": true
      },
      "trust": {
        "source_note": "Dựa trên dữ liệu giao dịch đã xác nhận.",
        "warning": null
      }
    }
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

## 12.5 Rendering rule

Frontend render mặc định:

```text
content
summary_metrics
evidence
actions
context_summary
```

Frontend load on-demand:

```text
related transactions
related insights
source details
```

## 12.6 Assistant intent routing

Assistant không tự đọc trực tiếp database. Assistant dùng tool layer có enforce `user_id`
server-side và route theo intent:

| User intent | Tool/API layer | Reads | Source-of-truth rule |
|---|---|---|---|
| `spending_summary` — “hôm qua tôi tiêu bao nhiêu?” | `query_spending_summary`, `search_transactions`, analytics tools | `transactions`, `budgets`, `categories` | Số tiền chính thức chỉ từ `transactions` |
| `receipt_lookup` — “xem hóa đơn tôi upload hôm qua” | `search_receipts`, receipt retrieval APIs | `receipt_uploads`, linked `transactions`, `invoices` | Chứng từ để truy xuất, không tính dashboard |
| `transaction_receipt_lookup` — “giao dịch này có hóa đơn không?” | `lookup_transaction_receipts`, `/transactions/{id}/receipt` | `transactions`, `receipt_uploads` | Link evidence hai chiều |
| Receipt content — “hóa đơn Highlands có món gì?” | `search_receipt_text`, line-item APIs | `receipt_text_chunks`, `receipt_line_items`, `invoice_line_items` | Nội dung chứng từ, không tự cộng tổng tiền |

Routing date semantics:

```text
created_date      = ngày upload chứng từ
receipt_date      = ngày ghi trên hóa đơn/chứng từ
transaction_date  = ngày giao dịch chính thức
```

---

# 13. Screen 8 — Settings

## 13.1 UI intent

Màn cài đặt quản lý:

```text
Hồ sơ cá nhân
Tùy chọn tài chính
Thông báo
Bảo mật
Quyền riêng tư & dữ liệu
AI & OCR
Gói dịch vụ
```

## 13.2 Components → API mapping

| Component | API | Method |
|---|---|---|
| Profile Card | `/users/me` | GET/PATCH |
| Avatar Upload | `/users/me/avatar` | POST/DELETE |
| Finance Settings | `/settings/finance` | GET/PATCH |
| Notification Settings | `/settings/notifications` | GET/PATCH |
| Change Password | `/auth/change-password` | POST |
| Active Sessions | `/security/sessions` | GET/DELETE |
| Login History | `/security/login-history` | GET |
| Privacy Settings | `/settings/privacy` | GET/PATCH |
| Export Data | `/data/export` | POST |
| Export Status | `/data/export/{export_id}` | GET |
| Delete Receipt Files | `/data/receipt-files` | DELETE |
| Account Delete Request | `/account/delete-request` | POST |
| AI/OCR Settings | `/settings/ai` | GET/PATCH |
| Billing Plan | `/billing/plan` | GET |
| Billing Usage | `/billing/usage` | GET |

## 13.3 Settings influence

| Setting | Affects |
|---|---|
| `default_currency` | Overview, Analytics, Transactions, Budget, Insights, Chat |
| `timezone` | Date range, OCR date, analytics grouping |
| `default_analytics_range` | Overview, Analytics, Insights, Chat |
| `budget_month_start_day` | Budget period calculation |
| `notifications` | Budget warnings, OCR completed, insight created |
| `allow_ai_data_processing` | OCR, Insights, Assistant |
| `auto_generate_insights` | Insights feed |
| `assistant_use_history` | Chat context |
| `receipt_file_retention_days` | Receipt file availability |
| `raw_prompt_retention_days` | AI privacy retention |

## 13.4 Example settings endpoint

```http
GET /api/v1/settings/finance
```

Response:

```json
{
  "data": {
    "default_currency": "VND",
    "timezone": "Asia/Ho_Chi_Minh",
    "budget_month_start_day": 1,
    "default_analytics_range": "30d",
    "number_format_locale": "vi-VN",
    "show_decimals": false
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```

---

# 14. Shared APIs

## 14.1 Categories

```http
GET /api/v1/categories
```

Used by:

```text
Transactions
Receipt Review
Analytics Filters
Budget Creation
Insights Filters
Chat Actions
```

## 14.2 Merchant search

```http
GET /api/v1/merchants/search?q=highlands&limit=10
```

Used by:

```text
Transaction form
Receipt Review merchant normalization
Analytics filters
```

## 14.3 Auth

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/logout
POST /api/v1/auth/change-password
```

---

# 15. Final endpoint map

## Analytics

```text
GET /api/v1/analytics/overview
GET /api/v1/analytics/trends
GET /api/v1/analytics/categories
GET /api/v1/analytics/categories/{category_id}
GET /api/v1/analytics/merchants
GET /api/v1/analytics/budgets
GET /api/v1/analytics/calendar
GET /api/v1/analytics/anomalies
GET /api/v1/analytics/insight-feed
```

## Receipts

```text
POST   /api/v1/receipts
GET    /api/v1/receipts
GET    /api/v1/receipts/{receipt_id}
GET    /api/v1/receipts/{receipt_id}/ocr-result
GET    /api/v1/receipts/{receipt_id}/draft
PATCH  /api/v1/receipts/{receipt_id}/draft
POST   /api/v1/receipts/{receipt_id}/confirm
POST   /api/v1/receipts/{receipt_id}/retry
DELETE /api/v1/receipts/{receipt_id}
```

## Transactions

```text
GET    /api/v1/transactions
POST   /api/v1/transactions
GET    /api/v1/transactions/{transaction_id}
PATCH  /api/v1/transactions/{transaction_id}
DELETE /api/v1/transactions/{transaction_id}
```

## Budgets

```text
GET    /api/v1/budgets
POST   /api/v1/budgets
PATCH  /api/v1/budgets/{budget_id}
DELETE /api/v1/budgets/{budget_id}
GET    /api/v1/budget-adjustments
```

## Insights

```text
GET   /api/v1/insights
GET   /api/v1/insights/{insight_id}
POST  /api/v1/insights/generate
PATCH /api/v1/insights/{insight_id}
POST  /api/v1/insights/{insight_id}/feedback
```

## Chat

```text
GET    /api/v1/chat/conversations
POST   /api/v1/chat/conversations
GET    /api/v1/chat/conversations/{conversation_id}/messages
POST   /api/v1/chat/messages
GET    /api/v1/chat/messages/{message_id}/result
POST   /api/v1/chat/messages/{message_id}/feedback
POST   /api/v1/chat/messages/{message_id}/regenerate
DELETE /api/v1/chat/conversations/{conversation_id}
```

## Settings

```text
GET    /api/v1/users/me
PATCH  /api/v1/users/me
POST   /api/v1/users/me/avatar
DELETE /api/v1/users/me/avatar

GET    /api/v1/settings/finance
PATCH  /api/v1/settings/finance
GET    /api/v1/settings/notifications
PATCH  /api/v1/settings/notifications
GET    /api/v1/settings/privacy
PATCH  /api/v1/settings/privacy
GET    /api/v1/settings/ai
PATCH  /api/v1/settings/ai

GET    /api/v1/security/sessions
DELETE /api/v1/security/sessions/{session_id}
DELETE /api/v1/security/sessions
GET    /api/v1/security/login-history

POST   /api/v1/data/export
GET    /api/v1/data/export/{export_id}
DELETE /api/v1/data/receipt-files
POST   /api/v1/account/delete-request
POST   /api/v1/account/delete-request/cancel
GET    /api/v1/audit-log

GET    /api/v1/billing/plan
GET    /api/v1/billing/usage
GET    /api/v1/billing/history
POST   /api/v1/billing/checkout-session
```

## Shared

```text
GET /api/v1/categories
GET /api/v1/merchants/search
```

## Health

```text
GET /health
GET /health/live
GET /health/ready
```

---

# 16. UI prototype mapping note

Vì hiện tại đang ở giai đoạn UI, frontend có thể dùng mock data nhưng nên đặt tên field gần với API contract.

## 16.1 Current mock → target API fields

| UI mock concept | Target API field |
|---|---|
| `id` | `transaction_id`, `receipt_id`, `budget_id` |
| `description` | `note` or `merchant.name` |
| `date` | `transaction_date` |
| `category` | `category.name` |
| `amount` | `amount` decimal string |
| `status` | `status` enum |
| `recognizedData` | `draft` / `ocr_result.normalized_payload` |

## 16.2 Frontend API client structure

```text
src/lib/api/
  analytics.ts
  transactions.ts
  receipts.ts
  budgets.ts
  insights.ts
  chat.ts
  settings.ts
  categories.ts
  merchants.ts
```

UI component không nên gọi fetch trực tiếp rải rác. Nên gọi qua API client để sau này thay mock bằng backend thật dễ hơn.

---

# 17. Database design handoff

Sau khi API Mapping này ổn, database sẽ thiết kế chi tiết theo các nhóm:

```text
users
transactions
receipt_uploads
ocr_results
receipt_line_items
invoices
invoice_line_items
categories
budgets
merchants
user_merchant_aliases
insights
chat_conversations
chat_messages
settings
security_sessions
audit_logs
billing_usage
```

Mỗi bảng cần xác định:

```text
fields
types
foreign keys
unique constraints
indexes
ownership rule
soft delete
retention rule
```

---

# 18. Implementation priority

## Phase 1 — UI mock alignment

```text
1. Đổi tên mock field theo API contract.
2. Tách API client layer.
3. Mỗi component map rõ endpoint tương lai.
4. Không cần backend thật ngay.
```

## Phase 2 — Backend core

```text
1. Auth/current user
2. Transactions API
3. Categories API
4. Receipts upload/poll/draft/confirm
5. Budgets API
```

## Phase 3 — Analytics

```text
1. Overview
2. Trends
3. Categories
4. Budgets
5. Merchants
6. Calendar
7. Anomalies
```

## Phase 4 — AI layer

```text
1. Rule-based insights
2. Insight feed
3. Chat assistant with evidence/actions
4. LLM narrative
```

## Phase 5 — Settings/security/data

```text
1. Finance settings
2. Notification settings
3. Privacy settings
4. AI/OCR settings
5. Security sessions
6. Data export/delete
```

---

# 19. Final decision

Bản v4 này là **API Mapping contract**, không phải database schema.

Nó dùng để đảm bảo:

```text
UI 8 màn có dữ liệu đúng
Backend biết endpoint cần xây
Database sau này thiết kế đúng nguồn dữ liệu
Chat/Insight không bịa số liệu
Receipt/OCR không bị tính nhầm vào dashboard
```

Thứ tự tiếp theo nên là:

```text
API Mapping v4
→ Database ERD/schema
→ Backend route/service design
→ Frontend API client integration
```
