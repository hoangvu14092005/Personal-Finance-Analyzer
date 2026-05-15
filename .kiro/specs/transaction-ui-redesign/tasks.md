# Tasks

## Task 1: Backend - Enhance TransactionResponse schema

- [x] 1.1 Add `has_invoice: bool` and `category_name: str | None` fields to `TransactionResponse` in `backend/api/app/schemas/transactions.py`
- [x] 1.2 Update `_to_response` helper in `backend/api/app/api/v1/transactions.py` to accept and pass `has_invoice` and `category_name`
- [x] 1.3 Update `list_transactions` endpoint to JOIN categories and check invoice existence, passing enriched data to response

## Task 2: Backend - Add GET /transactions/{id}/invoice endpoint

- [x] 2.1 Add `get_transaction_invoice` endpoint in `backend/api/app/api/v1/transactions.py` that resolves transaction → receipt → invoice
- [x] 2.2 Ensure ownership check and proper 404 responses for missing transaction, receipt, or invoice

## Task 3: Frontend - Update Transaction type and API client

- [x] 3.1 Add `has_invoice` and `category_name` fields to `Transaction` type in `frontend/web/lib/transactions-api.ts`
- [x] 3.2 Add `getTransactionInvoice(transactionId: number)` function to `frontend/web/lib/transactions-api.ts`

## Task 4: Frontend - Update transaction list display

- [x] 4.1 Add category name column and invoice indicator badge to the transaction table in `transaction-history-client.tsx`
- [x] 4.2 Add inline expandable detail row with invoice display, loading states, and error handling
