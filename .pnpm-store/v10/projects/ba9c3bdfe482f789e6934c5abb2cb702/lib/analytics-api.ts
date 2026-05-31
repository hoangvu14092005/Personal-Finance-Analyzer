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

export type ProductBreakdown = {
  item_name: string;
  total_amount: string;
  total_quantity: string;
  line_count: number;
  percentage: number;
};

export type AnalyticsProductsResponse = {
  range: RangeInfo;
  items: ProductBreakdown[];
};

export type SellerBreakdown = {
  seller_name: string;
  seller_tax_id: string | null;
  total_amount: string;
  invoice_count: number;
  percentage: number;
};

export type AnalyticsTaxResponse = {
  range: RangeInfo;
  subtotal_before_tax: string;
  total_tax: string;
  grand_total: string;
  invoice_count: number;
  effective_tax_rate: number;
  top_sellers: SellerBreakdown[];
};

export type AnalyticsReceiptStatsResponse = {
  range: RangeInfo;
  total_receipts: number;
  ready_count: number;
  failed_count: number;
  pending_count: number;
  with_invoice_count: number;
  confirmed_count: number;
  ocr_success_rate: number;
};

export type MerchantContribution = {
  merchant_name: string;
  current_amount: string;
  previous_amount: string;
  delta_amount: string;
};

export type CategoryDriver = {
  category_id: number | null;
  category_name: string;
  current_amount: string;
  previous_amount: string;
  delta_amount: string;
  delta_percent: number | null;
  direction: "increase" | "decrease" | string;
  top_merchants: MerchantContribution[];
};

export type AnalyticsDiagnosticsResponse = {
  range: RangeInfo;
  previous_range: RangeInfo;
  current_total: string;
  previous_total: string;
  delta_amount: string;
  delta_percent: number | null;
  drivers: CategoryDriver[];
};

export type MonthSpendForecast = {
  period_month: string;
  days_elapsed: number;
  days_in_month: number;
  spent_so_far: string;
  daily_run_rate: string;
  projected_total: string;
};

export type BudgetForecast = {
  category_id: number;
  category_name: string;
  budget_amount: string;
  spent_so_far: string;
  projected_spend: string;
  projected_percent: number;
  status: "on_track" | "warning" | "will_exceed" | "exceeded" | string;
  projected_exceed_date: string | null;
};

export type AnalyticsForecastResponse = {
  month: MonthSpendForecast;
  budgets: BudgetForecast[];
};

export type RecurringItem = {
  merchant_name: string;
  months_active: number;
  avg_monthly_amount: string;
  last_amount: string;
  last_date: string;
};

export type AnalyticsRecurringResponse = {
  lookback_months: number;
  fixed_monthly_estimate: string;
  variable_last_month: string;
  recurring_items: RecurringItem[];
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

export function getAnalyticsProducts(params: AnalyticsQuery & { limit?: number } = {}) {
  return apiRequest<AnalyticsProductsResponse>(`/api/v1/analytics/products${buildQuery(params)}`);
}

export function getAnalyticsTax(params: AnalyticsQuery & { sellers_limit?: number } = {}) {
  return apiRequest<AnalyticsTaxResponse>(`/api/v1/analytics/tax${buildQuery(params)}`);
}

export function getAnalyticsReceiptsStats(params: AnalyticsQuery = {}) {
  return apiRequest<AnalyticsReceiptStatsResponse>(`/api/v1/analytics/receipts-stats${buildQuery(params)}`);
}

export function getAnalyticsDiagnostics(params: AnalyticsQuery & { top_drivers?: number; compare?: "previous_period" | "year_ago" } = {}) {
  return apiRequest<AnalyticsDiagnosticsResponse>(`/api/v1/analytics/diagnostics${buildQuery(params)}`);
}

export function getAnalyticsForecast() {
  return apiRequest<AnalyticsForecastResponse>(`/api/v1/analytics/forecast`);
}

export function getAnalyticsRecurring(params: { lookback_months?: number } = {}) {
  return apiRequest<AnalyticsRecurringResponse>(`/api/v1/analytics/recurring${buildQuery(params)}`);
}
