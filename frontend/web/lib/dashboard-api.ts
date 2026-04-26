import { apiBaseUrl } from "@/lib/config";

// Match `app.services.date_ranges.RangePreset` của backend.
export const RANGE_PRESETS = [
  "7d",
  "30d",
  "this_month",
  "last_month",
  "custom",
] as const;
export type RangePreset = (typeof RANGE_PRESETS)[number];

export const DEFAULT_RANGE_PRESET: RangePreset = "30d";

export type RangeInfo = {
  preset: RangePreset;
  start: string; // ISO YYYY-MM-DD
  end: string;
  days: number;
};

export type CategoryBreakdown = {
  category_id: number | null;
  name: string;
  color: string | null;
  total_amount: string; // Decimal as string (giữ precision).
  transaction_count: number;
  percentage: number; // 0..100, đã round 2 decimals.
};

export type RecentTransaction = {
  id: number;
  merchant_name: string | null;
  amount: string;
  currency: string;
  transaction_date: string; // ISO date.
  category_id: number | null;
  category_name: string | null;
};

export type PeriodTotals = {
  total_spend: string;
  transaction_count: number;
};

export type DashboardSummary = {
  range: RangeInfo;
  previous_range: RangeInfo;
  current: PeriodTotals;
  previous: PeriodTotals;
  delta_amount: string;
  delta_percent: number | null; // null khi previous=0 (không thể tính %).
  top_categories: CategoryBreakdown[];
  recent_transactions: RecentTransaction[];
};

export type DashboardSummaryParams = {
  range?: RangePreset;
  start_date?: string; // Required khi range=custom.
  end_date?: string;
  top_categories_limit?: number;
  recent_transactions_limit?: number;
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
      // Non-JSON body; keep null and rely on status code.
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

function buildQuery(params: DashboardSummaryParams): string {
  const search = new URLSearchParams();
  if (params.range) search.set("range", params.range);
  if (params.start_date) search.set("start_date", params.start_date);
  if (params.end_date) search.set("end_date", params.end_date);
  if (params.top_categories_limit !== undefined) {
    search.set("top_categories_limit", String(params.top_categories_limit));
  }
  if (params.recent_transactions_limit !== undefined) {
    search.set(
      "recent_transactions_limit",
      String(params.recent_transactions_limit),
    );
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function getDashboardSummary(
  params: DashboardSummaryParams = {},
): Promise<DashboardSummary> {
  return request<DashboardSummary>(
    `/api/v1/dashboard/summary${buildQuery(params)}`,
    { method: "GET" },
  );
}

// Helpers cho UI.

export function isRangePreset(value: string | null | undefined): value is RangePreset {
  return value !== null && value !== undefined && (RANGE_PRESETS as readonly string[]).includes(value);
}

export const RANGE_LABELS: Record<RangePreset, string> = {
  "7d": "7 ngày qua",
  "30d": "30 ngày qua",
  this_month: "Tháng này",
  last_month: "Tháng trước",
  custom: "Tùy chỉnh",
};

export const PREVIOUS_RANGE_LABELS: Record<RangePreset, string> = {
  "7d": "So với 7 ngày trước đó",
  "30d": "So với 30 ngày trước đó",
  this_month: "So với tháng trước",
  last_month: "So với 2 tháng trước",
  custom: "So với kỳ trước cùng độ dài",
};
