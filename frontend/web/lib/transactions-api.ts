import { apiBaseUrl } from "@/lib/config";

// Server trả `amount` dưới dạng decimal string (Pydantic Decimal). Giữ string ở
// FE để tránh mất precision khi parse Number; format khi render.
export type Transaction = {
  id: number;
  user_id: number;
  category_id: number | null;
  category_name: string | null;
  receipt_upload_id: number | null;
  has_invoice: boolean;
  merchant_name: string | null;
  amount: string;
  currency: string;
  transaction_date: string; // ISO date YYYY-MM-DD
  note: string | null;
  created_at: string;
};

export type TransactionListMeta = {
  total: number;
  page: number;
  size: number;
};

export type TransactionListResponse = {
  items: Transaction[];
  meta: TransactionListMeta;
};

export type TransactionListFilters = {
  start_date?: string;
  end_date?: string;
  category_id?: number;
  merchant?: string;
  page?: number;
  size?: number;
};

export type TransactionUpdatePayload = Partial<{
  amount: string;
  currency: string;
  transaction_date: string;
  merchant_name: string | null;
  category_id: number | null;
  note: string | null;
}>;

export type TransactionCreatePayload = {
  amount: string;
  currency: string;
  transaction_date: string; // ISO YYYY-MM-DD
  merchant_name?: string | null;
  category_id?: number | null;
  receipt_upload_id?: number | null;
  note?: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      // Non-JSON body; keep null and rely on status code for messaging.
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

function buildQuery(filters: TransactionListFilters): string {
  const params = new URLSearchParams();
  if (filters.start_date) params.set("start_date", filters.start_date);
  if (filters.end_date) params.set("end_date", filters.end_date);
  if (filters.category_id !== undefined) {
    params.set("category_id", String(filters.category_id));
  }
  if (filters.merchant) params.set("merchant", filters.merchant);
  if (filters.page !== undefined) params.set("page", String(filters.page));
  if (filters.size !== undefined) params.set("size", String(filters.size));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function listTransactions(
  filters: TransactionListFilters = {},
): Promise<TransactionListResponse> {
  return request<TransactionListResponse>(
    `/api/v1/transactions${buildQuery(filters)}`,
    { method: "GET" },
  );
}

export async function createTransaction(
  payload: TransactionCreatePayload,
): Promise<Transaction> {
  return request<Transaction>(`/api/v1/transactions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateTransaction(
  id: number,
  payload: TransactionUpdatePayload,
): Promise<Transaction> {
  return request<Transaction>(`/api/v1/transactions/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteTransaction(id: number): Promise<void> {
  await request<void>(`/api/v1/transactions/${id}`, { method: "DELETE" });
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

export async function getTransactionInvoice(transactionId: number): Promise<InvoiceData> {
  return request<InvoiceData>(`/api/v1/transactions/${transactionId}/invoice`, {
    method: "GET",
  });
}
