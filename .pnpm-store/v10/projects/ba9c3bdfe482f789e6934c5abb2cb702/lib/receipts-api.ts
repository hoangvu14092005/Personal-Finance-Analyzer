import { apiBaseUrl } from "@/lib/config";

export type ReceiptStatus = {
  receipt_id: number;
  file_name: string;
  content_type: string;
  status: string;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
};

export type ReceiptUploadResult = {
  receipt_id: number;
  status: string;
};

export type LinkedTransaction = {
  transaction_id: number;
  status: string;
};

export type ReceiptListItem = {
  receipt_id: number;
  file_name: string;
  content_type: string;
  status: string;
  ocr_status: string;
  merchant_name: string | null;
  receipt_date: string | null;
  total_amount: string | null;
  currency: string | null;
  has_invoice: boolean;
  created_at: string;
  linked_transaction: LinkedTransaction | null;
};

export type ReceiptListMeta = {
  total: number;
  page: number;
  size: number;
};

export type ReceiptListResponse = {
  items: ReceiptListItem[];
  meta: ReceiptListMeta;
};

export type ReceiptListFilters = {
  receipt_date?: string;
  created_date?: string;
  merchant?: string;
  status?: string;
  ocr_status?: string;
  has_transaction?: boolean;
  has_invoice?: boolean;
  page?: number;
  size?: number;
};

export type DraftReview = {
  receipt_id: number;
  linked_transaction: LinkedTransaction | null;
  receipt_status: string;
  provider: string;
  confidence: number | null;
  merchant_name: string | null;
  transaction_date: string | null; // ISO YYYY-MM-DD or null
  amount: string | null; // Decimal string preserved precision
  currency: string | null;
  suggested_category_id: number | null;
  raw_text: string | null;
  line_items: ReceiptLineItem[];
};

export type ReceiptLineItem = {
  id: number;
  line_number: number;
  item_name: string;
  quantity: string;
  unit_price: string;
  total_price: string;
  category_id: number | null;
};

export type ReceiptConfirmPayload = {
  merchant_name?: string | null;
  transaction_date?: string | null;
  amount?: string | null;
  currency?: string | null;
  category_id?: number | null;
  note?: string | null;
  save_merchant_alias?: boolean;
};

export type ReceiptConfirmResult = {
  receipt_id: number;
  receipt_status: string;
  transaction_id: number;
};

async function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      // Keep null body for non-JSON; fallback message dùng status code.
    }
  }

  if (!response.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Request failed with status ${response.status}`;
    throw new Error(detail);
  }

  return body as T;
}

export async function uploadReceipt(file: File): Promise<ReceiptUploadResult> {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(`${apiBaseUrl}/api/v1/receipts/upload`, {
    method: "POST",
    body: form,
    credentials: "include",
  });

  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      // No-op: body stays null; status code dẫn lỗi.
    }
  }

  if (!response.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Upload failed with status ${response.status}`;
    throw new Error(detail);
  }

  return body as ReceiptUploadResult;
}

export async function getReceiptStatus(receiptId: number): Promise<ReceiptStatus> {
  return jsonRequest<ReceiptStatus>(`/api/v1/receipts/${receiptId}`, { method: "GET" });
}

export async function getReceiptDraft(receiptId: number): Promise<DraftReview> {
  return jsonRequest<DraftReview>(`/api/v1/receipts/${receiptId}/draft`, { method: "GET" });
}

function buildReceiptQuery(filters: ReceiptListFilters): string {
  const params = new URLSearchParams();
  if (filters.receipt_date) params.set("receipt_date", filters.receipt_date);
  if (filters.created_date) params.set("created_date", filters.created_date);
  if (filters.merchant) params.set("merchant", filters.merchant);
  if (filters.status) params.set("status", filters.status);
  if (filters.ocr_status) params.set("ocr_status", filters.ocr_status);
  if (filters.has_transaction !== undefined) {
    params.set("has_transaction", String(filters.has_transaction));
  }
  if (filters.has_invoice !== undefined) {
    params.set("has_invoice", String(filters.has_invoice));
  }
  if (filters.page !== undefined) params.set("page", String(filters.page));
  if (filters.size !== undefined) params.set("size", String(filters.size));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function listReceipts(
  filters: ReceiptListFilters = {},
): Promise<ReceiptListResponse> {
  return jsonRequest<ReceiptListResponse>(
    `/api/v1/receipts${buildReceiptQuery(filters)}`,
    { method: "GET" },
  );
}

export async function confirmReceipt(
  receiptId: number,
  payload: ReceiptConfirmPayload,
): Promise<ReceiptConfirmResult> {
  return jsonRequest<ReceiptConfirmResult>(`/api/v1/receipts/${receiptId}/confirm`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type InvoiceLineItem = {
  id: number;
  line_number: number;
  item_name: string;
  unit: string | null;
  quantity: string;
  unit_price: string;
  line_total: string;
  vat_rate: string | null;
  vat_amount: string | null;
};

export type InvoiceData = {
  id: number;
  receipt_upload_id: number;
  invoice_number: string | null;
  template_symbol: string | null;
  issue_date: string | null;
  tax_lookup_code: string | null;
  currency: string;
  seller_name: string | null;
  seller_tax_id: string | null;
  seller_address: string | null;
  buyer_name: string | null;
  buyer_tax_id: string | null;
  buyer_address: string | null;
  payment_method: string | null;
  subtotal_before_tax: string | null;
  total_tax: string | null;
  grand_total: string | null;
  amount_in_words: string | null;
  digital_signature: string | null;
  signing_date: string | null;
  lookup_link: string | null;
  line_items: InvoiceLineItem[];
};

export async function getReceiptInvoice(receiptId: number): Promise<InvoiceData> {
  return jsonRequest<InvoiceData>(`/api/v1/receipts/${receiptId}/invoice`, { method: "GET" });
}
