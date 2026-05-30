import { apiRequest, buildQuery } from "@/lib/api-client";
import type { RangePreset } from "@/lib/dashboard-api";

export type InsightSeverity = "info" | "success" | "watch" | "warning" | "danger";
export type InsightStatus = "active" | "dismissed" | "expired";

export type Insight = {
  id: number;
  type: string;
  severity: InsightSeverity;
  title: string;
  summary: string;
  evidence: Record<string, unknown>[];
  actions: Record<string, unknown>[];
  range_start: string;
  range_end: string;
  status: InsightStatus;
  dismissed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type InsightListResponse = {
  items: Insight[];
  has_more: boolean;
  next_before_id: number | null;
};

export type InsightGenerateResponse = {
  items: Insight[];
  generated_count: number;
};

export type InsightFeedbackRating = "helpful" | "not_helpful" | "irrelevant";

export function listInsights(params: {
  status?: InsightStatus;
  type?: string;
  severity?: InsightSeverity;
  limit?: number;
  before_id?: number | null;
} = {}) {
  return apiRequest<InsightListResponse>(`/api/v1/insights${buildQuery(params)}`);
}

export function generateInsights(payload: {
  range?: RangePreset;
  start_date?: string;
  end_date?: string;
  force_refresh?: boolean;
  types?: string[] | null;
} = {}) {
  return apiRequest<InsightGenerateResponse>("/api/v1/insights/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateInsightStatus(id: number, status: "active" | "dismissed") {
  return apiRequest<Insight>(`/api/v1/insights/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function sendInsightFeedback(id: number, rating: InsightFeedbackRating, comment?: string) {
  return apiRequest<{ id: number; insight_id: number; rating: InsightFeedbackRating; comment: string | null; created_at: string }>(`/api/v1/insights/${id}/feedback`, {
    method: "POST",
    body: JSON.stringify({ rating, comment: comment || null }),
  });
}
