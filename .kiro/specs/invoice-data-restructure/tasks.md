# Tasks

## Task 1: Add Invoice and InvoiceLineItem entities
- [x] 1.1 Add `Invoice` SQLModel entity to `backend/shared/pfa_shared/entities.py` with all fields (metadata, seller, buyer, totals, authentication, FKs)
- [x] 1.2 Add `InvoiceLineItem` SQLModel entity to `backend/shared/pfa_shared/entities.py` with all fields (item_name, unit, quantity, unit_price, line_total, vat_rate, vat_amount, line_number)
- [x] 1.3 Update `__all__` export list in entities.py to include new entities
- [x] 1.4 Add table creation SQL for `invoices` and `invoice_line_items` in `backend/api/app/main.py` `_ensure_tables()`

## Task 2: Update OCR Provider with invoice extraction
- [x] 2.1 Add `OCRInvoiceLineItem` and `OCRInvoiceResult` dataclasses to `backend/worker/ocr_provider.py`
- [x] 2.2 Add `OCR_INVOICE_NORMALIZE_PROMPT` for Vietnamese e-invoice parsing
- [x] 2.3 Add `normalize_invoice()` method to `LLMVisionOCRProvider`
- [x] 2.4 Add `_parse_invoice_normalized()` helper function with defensive parsing
- [x] 2.5 Add `normalize_invoice()` to `MockOCRProvider` returning sample Vietnamese invoice data
- [x] 2.6 Add `normalize_invoice()` to `OCRProvider` Protocol

## Task 3: Update Worker task to save Invoice data
- [x] 3.1 Add `_save_invoice()` helper function in `backend/worker/tasks.py`
- [x] 3.2 Update `run_ocr_for_receipt()` to call `provider.normalize_invoice()` and `_save_invoice()` after existing OCR flow
- [x] 3.3 Implement line_total auto-calculation (quantity × unit_price) when OCR returns None

## Task 4: Add API schemas and endpoint for Invoice
- [x] 4.1 Add `InvoiceLineItemResponse` and `InvoiceResponse` Pydantic schemas to `backend/api/app/schemas/receipts.py`
- [x] 4.2 Add `GET /receipts/{receipt_id}/invoice` endpoint in `backend/api/app/api/v1/receipts.py`
- [x] 4.3 Update `get_receipt_draft` endpoint to prefer Invoice data when available (seller_name→merchant, grand_total→amount, issue_date→date)

## Task 5: Update Frontend types and API client
- [x] 5.1 Add `InvoiceLineItem` and `InvoiceData` TypeScript types to `frontend/web/lib/receipts-api.ts`
- [x] 5.2 Add `getReceiptInvoice()` API function to `frontend/web/lib/receipts-api.ts`

## Task 6: Property-based tests
- [ ] 6.1 Write property test: Invoice persistence round-trip (Property 1)
- [ ] 6.2 Write property test: line_total auto-calculation (Property 2)
- [ ] 6.3 Write property test: OCR parser resilience with partial data (Property 3)
- [ ] 6.4 Write property test: Worker saves complete Invoice structure (Property 4)
- [ ] 6.5 Write property test: Worker idempotency on re-processing (Property 5)
- [ ] 6.6 Write property test: API prefers Invoice over OcrResult (Property 6)
