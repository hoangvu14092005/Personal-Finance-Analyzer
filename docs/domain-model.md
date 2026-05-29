# Domain model source of truth

This document describes the intended ownership and data-source boundaries for
the current schema. It should be kept in sync with `backend/shared/pfa_shared/entities.py`.

## Source-of-truth rules

- Financial reporting reads from `transactions`.
- Receipt and OCR tables are input/review/debug data, not reporting truth.
- Chat messages store conversation history only, not financial facts.
- RAG tables support search over text and semantic hints; SQL over transactions remains authoritative for money.

## Merchant normalization

`merchants` stores global normalized merchants. `user_merchant_aliases` stores
user-specific raw names from OCR/manual entry and their preferred category.

During the transition, `transactions.merchant_name` and
`user_merchant_mappings` remain for compatibility. New writes also populate:

- `transactions.raw_merchant_name`
- `transactions.merchant_id`
- `transactions.source`
- `user_merchant_aliases`

## Receipt and invoice boundaries

- A normal receipt may create `receipt_line_items`.
- A Vietnamese e-invoice may create `invoices` and `invoice_line_items`.
- Both may create one aggregate `transactions` row for reporting.
- Line items are detail data unless the product explicitly chooses item-level transactions later.

## User ownership

All user data should be scoped by `user_id`. Service code must ensure related
rows belong to the same user, especially for categories, receipts, invoices,
line items, merchant aliases, text chunks, and transactions.

Category access rule:

```text
category.user_id == current_user.id OR category.user_id is null/system
```

Receipt-derived data rule:

```text
related.receipt_upload_id -> receipt_uploads.user_id == current_user.id
```

## Query routing for AI

- Spending totals, trends, budgets: SQL over `transactions` and `budgets`.
- Receipt text details: `receipt_text_chunks`, `receipt_line_items`, or `invoice_line_items`.
- Fuzzy merchant/product memory: `transactions.search_embedding` and merchant aliases.
