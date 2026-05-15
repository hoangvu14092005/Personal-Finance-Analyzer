# Requirements Document

## Introduction

Redesign the transaction display in the frontend to show full invoice details when available, and ensure the OCR-to-database flow works end-to-end. Currently, the transactions list page only shows basic info (merchant, amount, date, note). Transactions created from OCR receipts have associated Invoice entities with rich Vietnamese e-invoice data (seller/buyer info, line items with VAT, totals, digital signature) that should be viewable from the transactions page.

## Glossary

- **Transaction_List_Page**: The frontend page at `/transactions` that displays a paginated, filterable list of user transactions.
- **Transaction_Detail_View**: An expandable or modal view showing full transaction details including associated invoice data.
- **Invoice**: A Vietnamese e-invoice (hóa đơn điện tử) entity containing metadata, seller/buyer info, line items, totals, and authentication data.
- **Invoice_Line_Item**: A single product/service entry within an Invoice, including unit, quantity, price, VAT rate, and VAT amount.
- **Transactions_API**: The backend REST API at `/api/v1/transactions` serving transaction data.
- **OCR_Worker**: The background worker that processes uploaded receipts via OCR, saves Invoice + InvoiceLineItem entities, and auto-creates a Transaction.
- **Frontend_App**: The Next.js web application rendering the user interface.

## Requirements

### Requirement 1: Transaction Detail API Endpoint

**User Story:** As a user, I want to retrieve full invoice details for a transaction, so that I can view the complete e-invoice data from the transactions page without navigating to the receipt review page.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/v1/transactions/{id}/invoice`, THE Transactions_API SHALL return the full Invoice with nested line items for the transaction's associated receipt.
2. IF the transaction has no associated receipt or no Invoice exists for the receipt, THEN THE Transactions_API SHALL return a 404 status with a descriptive error message.
3. THE Transactions_API SHALL verify that the requesting user owns the transaction before returning invoice data.
4. THE Transactions_API SHALL return invoice data in the same schema as the existing `/api/v1/receipts/{id}/invoice` endpoint (InvoiceResponse with nested InvoiceLineItemResponse).

### Requirement 2: Transaction List with Invoice Indicator

**User Story:** As a user, I want to see which transactions have associated invoices in the list view, so that I can quickly identify which ones have detailed invoice data available.

#### Acceptance Criteria

1. WHEN the transaction list is loaded, THE Transactions_API SHALL include a boolean field `has_invoice` in each transaction response indicating whether an Invoice entity exists for that transaction's receipt.
2. THE Frontend_App SHALL display a visual indicator (icon or badge) on transactions that have associated invoice data.
3. THE Frontend_App SHALL render the indicator without requiring additional API calls per transaction (the indicator data comes from the list response).

### Requirement 3: Transaction Detail View with Invoice Display

**User Story:** As a user, I want to click on a transaction to see its full invoice details, so that I can review seller/buyer info, line items, totals, and authentication data.

#### Acceptance Criteria

1. WHEN a user clicks on a transaction row that has an associated invoice, THE Frontend_App SHALL display a detail view showing the full invoice information.
2. THE Transaction_Detail_View SHALL display invoice metadata: invoice number, template symbol, issue date, tax lookup code, and currency.
3. THE Transaction_Detail_View SHALL display seller information: name, tax ID, and address.
4. THE Transaction_Detail_View SHALL display buyer information: name, tax ID, address, and payment method.
5. THE Transaction_Detail_View SHALL display a line items table with columns: item name, unit, quantity, unit price, line total, VAT rate, and VAT amount.
6. THE Transaction_Detail_View SHALL display totals: subtotal before tax, total tax, grand total, and amount in words.
7. THE Transaction_Detail_View SHALL display authentication info: digital signature status, signing date, and lookup link (as a clickable external link).
8. WHEN a user clicks on a transaction that has no associated invoice, THE Frontend_App SHALL show only the basic transaction details (amount, merchant, date, note, category).

### Requirement 4: OCR-to-Transaction End-to-End Flow Integrity

**User Story:** As a user, I want the OCR upload flow to reliably create both Invoice data and a Transaction, so that my uploaded receipts appear in the transactions list with full invoice details.

#### Acceptance Criteria

1. WHEN the OCR_Worker processes a receipt, THE OCR_Worker SHALL save an Invoice entity with all extracted fields (metadata, seller, buyer, totals, authentication).
2. WHEN the OCR_Worker processes a receipt, THE OCR_Worker SHALL save InvoiceLineItem entities for each line item extracted from the invoice.
3. WHEN the OCR_Worker processes a receipt, THE OCR_Worker SHALL auto-create a Transaction linked to the receipt with the invoice's grand_total as amount, seller_name as merchant, and issue_date as transaction_date.
4. IF a Transaction already exists for the receipt, THEN THE OCR_Worker SHALL skip transaction creation (idempotent behavior).
5. THE Transaction created by OCR_Worker SHALL be visible in the Transaction_List_Page with the `has_invoice` indicator set to true.

### Requirement 5: Transaction Detail View Interaction Design

**User Story:** As a user, I want a smooth interaction pattern for viewing transaction details, so that I can quickly browse through transactions and their invoices without losing my place in the list.

#### Acceptance Criteria

1. WHEN a user clicks a transaction row, THE Frontend_App SHALL expand the row inline or open a slide-over panel to show the detail view (without navigating away from the list page).
2. WHEN the detail view is open and the user clicks the same transaction again or clicks a close button, THE Frontend_App SHALL collapse or close the detail view.
3. WHILE the detail view is loading invoice data, THE Frontend_App SHALL display a loading indicator in the detail area.
4. IF loading invoice data fails, THEN THE Frontend_App SHALL display an error message within the detail view without disrupting the transaction list.

### Requirement 6: Transaction List Enhanced Display

**User Story:** As a user, I want the transaction list to show category information alongside existing fields, so that I have better context when browsing transactions.

#### Acceptance Criteria

1. WHEN the transaction list is loaded, THE Transactions_API SHALL include the category name in the transaction response (resolved from category_id).
2. THE Frontend_App SHALL display the category name in the transaction list table as an additional column or badge.
3. IF a transaction has no category assigned, THE Frontend_App SHALL display a neutral placeholder text.
