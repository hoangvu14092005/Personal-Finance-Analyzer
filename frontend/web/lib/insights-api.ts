// Frontend client cho AI Insights API (Phase 6.10).
// Endpoints:
// - POST /api/v1/insights/generate
// - GET  /api/v1/insights/latest?range=...
//
// Schema khớp Pydantic ở backend (`app/schemas/insights.py`). Type
// `InsightStatus` cover cả "ready" / "insufficient_data" / "failed" để
// UI render conditional state.

import { apiBaseUrl } from "@/lib/config";
import type { RangePreset } from "@/lib/dashboard-api";

export type InsightStatus = "ready" | "insufficient_data" | "failed";

export type InsightItem = {
  title: string;
  body: string;
  category_id: number | null;
};

export type RecommendationItem = {
  title: string;
  body: string;
  estimated_savings: string | null; // Decimal as string.
  category_id: number | null;
};

export type AlertSeverity = "info" | "warning" | "critical";

export type AlertItem = {
  title: string;
  body: string;
  severity: AlertSeverity;
  category_id: number | null;
};

export type InsightPayload = {
  insights: InsightItem[];
  recommendations: RecommendationItem[];
  alerts: AlertItem[];
};

export type InsightRangeInfo = {
  preset: string;
  start: string; // ISO YYYY-MM-DD.
  end: string;
};

export type InsightResponse = {
  id: number | null;
  range: InsightRangeInfo;
  status: InsightStatus;
  status_reason: string | null;
  provider: string;
  fingerprint: string;
  payload: InsightPayload;
  generated_at: string; // ISO datetime UTC.
  cached: boolean;
};

export type GenerateInsightRequest = {
  range?: RangePreset;
  start_date?: string;
  end_date?: string;
  force?: boolean;
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
      // Non-JSON body — keep null and rely on status.
    }
  }

  if (!response.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Request failed with status ${response.status}`;
    const error = new Error(detail) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }

  return body as T;
}

export async function generateInsight(
  payload: GenerateInsightRequest = {},
): Promise<InsightResponse> {
  return request<InsightResponse>("/api/v1/insights/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getLatestInsight(
  range: RangePreset = "30d",
): Promise<InsightResponse> {
  const search = new URLSearchParams({ range });
  return request<InsightResponse>(
    `/api/v1/insights/latest?${search.toString()}`,
    { method: "GET" },
  );
}

// UI helpers.

export const INSIGHT_STATUS_LABELS: Record<InsightStatus, string> = {
  ready: "Sẵn sàng",
  insufficient_data: "Chưa đủ dữ liệu",
  failed: "Tạo insight thất bại",
};

export const ALERT_SEVERITY_LABELS: Record<AlertSeverity, string> = {
  info: "Thông tin",
  warning: "Cảnh báo",
  critical: "Nghiêm trọng",
};

export function isInsightEmpty(payload: InsightPayload): boolean {
  return (
    payload.insights.length === 0 &&
    payload.recommendations.length === 0 &&
    payload.alerts.length === 0
  );
}
