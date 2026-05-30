import { apiRequest, buildQuery } from "@/lib/api-client";

export type SecuritySession = {
  id: string;
  user_id: number;
  email: string;
  is_current: boolean;
  created_at: string;
};

export type LoginHistoryItem = {
  id: string;
  occurred_at: string;
  event: string;
  ip_address: string | null;
  user_agent: string | null;
};

export type BillingPlan = {
  plan_id: string;
  name: string;
  status: string;
  currency: string;
  monthly_price: string;
  features: string[];
};

export type BillingUsage = {
  transaction_count: number;
  receipt_count: number;
  invoice_count: number;
  insight_count: number;
  storage_backend: string;
};

export type DataExport = {
  export_id: string;
  status: "queued" | "ready" | "failed";
  created_at: string;
  expires_at: string | null;
  download_url: string | null;
  message: string | null;
  included: string[];
};

export type AuditLogItem = {
  id: string;
  event: string;
  occurred_at: string;
  actor_user_id: number;
  target_type: string | null;
  target_id: string | null;
  metadata: Record<string, string>;
};

export function listSecuritySessions() {
  return apiRequest<{ items: SecuritySession[] }>("/api/v1/security/sessions");
}

export function listLoginHistory() {
  return apiRequest<{ items: LoginHistoryItem[] }>("/api/v1/security/login-history");
}

export function revokeCurrentSession() {
  return apiRequest<void>("/api/v1/security/sessions/current", { method: "DELETE" });
}

export function getBillingPlan() {
  return apiRequest<BillingPlan>("/api/v1/billing/plan");
}

export function getBillingUsage() {
  return apiRequest<BillingUsage>("/api/v1/billing/usage");
}

export function createCheckoutSession() {
  return apiRequest<{ status: string; checkout_url: string | null; message: string }>("/api/v1/billing/checkout-session", { method: "POST" });
}

export function createDataExport(payload = { include_receipts: true, include_transactions: true, include_chat: true }) {
  return apiRequest<DataExport>("/api/v1/data/export", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listAuditLog(limit = 20) {
  return apiRequest<{ items: AuditLogItem[] }>(`/api/v1/audit-log${buildQuery({ limit })}`);
}
