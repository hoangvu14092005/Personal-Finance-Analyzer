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

export type DraftReview = {
  receipt_id: number;
  receipt_status: string;
  provider: string;
  confidence: number | null;
  merchant_name: string | null;
  transaction_date: string | null; // ISO YYYY-MM-DD or null
  amount: string | null; // Decimal string preserved precision
  currency: string | null;
  suggested_category_id: number | null;
  raw_text: string | null;
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
