# Requirements Document

## Introduction

Tái cấu trúc data model hóa đơn (invoice) trong ứng dụng Personal Finance Analyzer để hỗ trợ đầy đủ cấu trúc hóa đơn điện tử Việt Nam (e-invoice). Hiện tại hệ thống chỉ lưu thông tin tối thiểu (merchant, total_amount, transaction_date, currency). Yêu cầu mới mở rộng schema để lưu trữ toàn bộ thông tin hóa đơn bao gồm: thông tin hóa đơn, người bán, người mua, chi tiết hàng hóa với thuế VAT, tổng tiền chi tiết, và thông tin ký số/xác thực.

## Glossary

- **Invoice**: Entity chính lưu trữ toàn bộ thông tin hóa đơn điện tử, liên kết 1-1 với ReceiptUpload
- **Seller**: Thông tin người bán hàng trên hóa đơn (tên, MST, địa chỉ)
- **Buyer**: Thông tin người mua hàng trên hóa đơn (tên, MST, địa chỉ, hình thức thanh toán)
- **InvoiceLineItem**: Một dòng hàng hóa/dịch vụ trên hóa đơn, bao gồm thuế VAT
- **OCR_Provider**: Module trích xuất text từ ảnh/PDF hóa đơn và parse thành structured data
- **Worker**: TaskIQ background worker xử lý OCR job và lưu kết quả vào database
- **API_Server**: FastAPI backend phục vụ REST endpoints cho frontend
- **Frontend**: Next.js web application hiển thị và cho phép review hóa đơn
- **VAT_Rate**: Thuế suất giá trị gia tăng (0%, 5%, 8%, 10%)
- **Digital_Signature**: Chữ ký số xác thực hóa đơn điện tử

## Requirements

### Requirement 1: Invoice Entity Schema

**User Story:** As a developer, I want a comprehensive Invoice database entity that stores all Vietnamese e-invoice fields, so that the system can persist full invoice data extracted from OCR.

#### Acceptance Criteria

1. THE Invoice entity SHALL store invoice metadata: invoice_number, template_symbol, issue_date, tax_lookup_code, and currency
2. THE Invoice entity SHALL store seller information: seller_name, seller_tax_id, and seller_address
3. THE Invoice entity SHALL store buyer information: buyer_name, buyer_tax_id, buyer_address, and payment_method
4. THE Invoice entity SHALL store totals: subtotal_before_tax, total_tax, grand_total, and amount_in_words
5. THE Invoice entity SHALL store authentication info: digital_signature, signing_date, and lookup_link
6. THE Invoice entity SHALL reference the ReceiptUpload via a one-to-one foreign key relationship
7. THE Invoice entity SHALL reference the owning User via a foreign key relationship

### Requirement 2: Invoice Line Item Schema with VAT

**User Story:** As a developer, I want invoice line items to include VAT information, so that tax calculations are accurately captured per item.

#### Acceptance Criteria

1. THE InvoiceLineItem entity SHALL store: item_name, unit, quantity, unit_price, and line_total
2. THE InvoiceLineItem entity SHALL store VAT fields: vat_rate as a decimal percentage and vat_amount as a monetary value
3. THE InvoiceLineItem entity SHALL reference the parent Invoice via a foreign key with CASCADE delete
4. THE InvoiceLineItem entity SHALL store a line_number field to preserve ordering within the invoice
5. WHEN line_total is not provided by OCR, THE Worker SHALL calculate line_total as quantity multiplied by unit_price

### Requirement 3: OCR Provider Structured Extraction

**User Story:** As a developer, I want the OCR provider to extract all Vietnamese e-invoice fields from receipt images, so that the full invoice structure is populated automatically.

#### Acceptance Criteria

1. THE OCR_Provider SHALL extract invoice metadata fields: invoice_number, template_symbol, issue_date, tax_lookup_code, and currency from receipt images
2. THE OCR_Provider SHALL extract seller fields: seller_name, seller_tax_id, and seller_address from receipt images
3. THE OCR_Provider SHALL extract buyer fields: buyer_name, buyer_tax_id, buyer_address, and payment_method from receipt images
4. THE OCR_Provider SHALL extract line items with: item_name, unit, quantity, unit_price, line_total, vat_rate, and vat_amount from receipt images
5. THE OCR_Provider SHALL extract totals: subtotal_before_tax, total_tax, grand_total, and amount_in_words from receipt images
6. THE OCR_Provider SHALL extract authentication info: digital_signature presence, signing_date, and lookup_link from receipt images
7. IF the OCR_Provider cannot extract a field, THEN THE OCR_Provider SHALL return null for that field without failing the entire extraction
8. THE OCR_Provider SHALL return a structured dataclass (OCRInvoiceResult) containing all extracted fields

### Requirement 4: Worker Task Saves Full Invoice Data

**User Story:** As a developer, I want the OCR worker task to persist the full invoice structure into the database, so that extracted data is available for API queries.

#### Acceptance Criteria

1. WHEN OCR extraction completes successfully, THE Worker SHALL create an Invoice record with all extracted metadata, seller, buyer, totals, and authentication fields
2. WHEN OCR extraction completes successfully, THE Worker SHALL create InvoiceLineItem records for each extracted line item
3. WHEN re-processing an existing receipt, THE Worker SHALL delete existing Invoice and InvoiceLineItem records before inserting new ones (idempotent behavior)
4. WHEN OCR extraction fails, THE Worker SHALL mark the receipt status as FAILED with an appropriate error message without creating partial Invoice records
5. THE Worker SHALL maintain backward compatibility by continuing to create the existing OcrResult record alongside the new Invoice record

### Requirement 5: API Endpoints Return Full Invoice Data

**User Story:** As a user, I want the API to return complete invoice information, so that I can review all extracted fields in the frontend.

#### Acceptance Criteria

1. THE API_Server SHALL provide a GET endpoint at /api/v1/receipts/{receipt_id}/invoice that returns the full Invoice with nested line items
2. THE API_Server SHALL return 404 when no Invoice exists for the given receipt_id
3. THE API_Server SHALL verify that the requesting user owns the receipt before returning invoice data
4. THE API_Server SHALL include all invoice fields: metadata, seller, buyer, line items with VAT, totals, and authentication info in the response
5. THE API_Server SHALL update the existing draft endpoint to include invoice-level fields when an Invoice record exists

### Requirement 6: Frontend Displays Full Invoice

**User Story:** As a user, I want to see all invoice details on the review page, so that I can verify the OCR extraction accuracy before confirming.

#### Acceptance Criteria

1. THE Frontend SHALL display invoice metadata section: invoice number, template/symbol, issue date, tax lookup code, and currency
2. THE Frontend SHALL display seller information section: name, tax ID, and address
3. THE Frontend SHALL display buyer information section: name, tax ID, address, and payment method
4. THE Frontend SHALL display line items in a table with columns: item name, unit, quantity, unit price, line total, VAT rate, and VAT amount
5. THE Frontend SHALL display totals section: subtotal before tax, total tax, grand total, and amount in words
6. THE Frontend SHALL display authentication section: digital signature status, signing date, and lookup link
7. WHEN a field value is null, THE Frontend SHALL display a placeholder indicator instead of empty space

### Requirement 7: Data Migration Compatibility

**User Story:** As a developer, I want the new schema to coexist with existing data, so that previously processed receipts remain accessible without re-processing.

#### Acceptance Criteria

1. THE Invoice entity SHALL be nullable from the ReceiptUpload perspective (existing receipts without Invoice records remain valid)
2. THE API_Server SHALL gracefully handle receipts that have OcrResult but no Invoice record by falling back to the existing draft response format
3. WHEN a receipt has both OcrResult and Invoice records, THE API_Server SHALL prefer Invoice data in the response
