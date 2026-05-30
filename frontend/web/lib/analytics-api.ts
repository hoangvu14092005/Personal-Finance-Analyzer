import { apiRequest, buildQuery } from "@/lib/api-client";
import type { BudgetUsage } from "@/lib/budgets-api";
import type { CategoryBreakdown, DashboardSummary, DashboardSummaryParams, RangeInfo, RangePreset } from "@/lib/dashboard-api";
import type { Insight } from "@/lib/insights-api";

export type TrendPoint = {
  period_start: string;
  period_end: string;
  amount: string;
  transaction_count: number;
};

export type AnalyticsTrendsResponse = {
  range: RangeInfo;
  group_by: "day" | "week" | "month" | string;
  points: TrendPoint[];
};

export type MerchantBreakdown = {
  merchant_name: string;
  total_amount: string;
  transaction_count: number;
  percentage: number;
};

export type AnalyticsMerchantsResponse = {
  range: RangeInfo;
  items: MerchantBreakdown[];
};

export type CalendarDay = {
  date: string;
  amount: string;
  transaction_count: number;
  intensity: number;
  top_category_name: string | null;
  is_unusual: boolean;
};

export type AnalyticsCalendarResponse = {
  range: RangeInfo;
  days: CalendarDay[];
  legend: { levels: Record<string, string> };
};

export type AnalyticsAnomaly = {
  id: string;
  type: string;
  severity: string;
  title: string;
  transaction_id: number;
  merchant_name: string | null;
  transaction_date: string;
  amount: string;
  baseline_amount: string;
  reason: string;
};

export type AnalyticsAnomaliesResponse = {
  range: RangeInfo;
  anomalies: AnalyticsAnomaly[];
};

export type AnalyticsBudgetsResponse = {
  period_month: string;
  total_budget: string;
  total_spent: string;
  remaining_amount: string;
  exceeded_count: number;
  warning_count: number;
  budgets: BudgetUsage[];
};

export type AnalyticsInsightFeedResponse = {
  range: RangeInfo;
  hero: Insight | null;
  insights: Insight[];
  source: string;
  meta: Record<string, unknown>;
};

export type AnalyticsCategoriesResponse = {
  range: RangeInfo;
  items: CategoryBreakdown[];
};

export type AnalyticsQuery = {
  range?: RangePreset;
  start_date?: string;
  end_date?: string;
};

export function getAnalyticsOverview(params: DashboardSummaryParams = {}) {
  return apiRequest<DashboardSummary>(`/api/v1/analytics/overview${buildQuery(params)}`);
}

export function getAnalyticsTrends(params: AnalyticsQuery & { group_by?: "day" | "week" | "month" } = {}) {
  return apiRequest<AnalyticsTrendsResponse>(`/api/v1/analytics/trends${buildQuery(params)}`);
}

export function getAnalyticsCategories(params: AnalyticsQuery & { limit?: number } = {}) {
  return apiRequest<AnalyticsCategoriesResponse>(`/api/v1/analytics/categories${buildQuery(params)}`);
}

export function getAnalyticsMerchants(params: AnalyticsQuery & { limit?: number } = {}) {
  return apiRequest<AnalyticsMerchantsResponse>(`/api/v1/analytics/merchants${buildQuery(params)}`);
}

export function getAnalyticsCalendar(params: AnalyticsQuery = {}) {
  return apiRequest<AnalyticsCalendarResponse>(`/api/v1/analytics/calendar${buildQuery(params)}`);
}

export function getAnalyticsAnomalies(params: AnalyticsQuery & { limit?: number } = {}) {
  return apiRequest<AnalyticsAnomaliesResponse>(`/api/v1/analytics/anomalies${buildQuery(params)}`);
}

export function getAnalyticsBudgets(periodMonth: string) {
  return apiRequest<AnalyticsBudgetsResponse>(`/api/v1/analytics/budgets${buildQuery({ period_month: periodMonth })}`);
}

export function getAnalyticsInsightFeed(params: AnalyticsQuery & { limit?: number; auto_generate?: boolean } = {}) {
  return apiRequest<AnalyticsInsightFeedResponse>(`/api/v1/analytics/insight-feed${buildQuery(params)}`);
}
