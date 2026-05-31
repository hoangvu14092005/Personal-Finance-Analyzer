"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Calendar,
  Car,
  Coffee,
  FileText,
  Gamepad2,
  HeartPulse,
  PieChart,
  Receipt,
  ShoppingBag,
  Sparkles,
  Store,
  TrendingDown,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

import { getMe } from "@/lib/auth-api";
import {
  AnalyticsAnomaliesResponse,
  AnalyticsCalendarResponse,
  AnalyticsDiagnosticsResponse,
  AnalyticsForecastResponse,
  AnalyticsMerchantsResponse,
  AnalyticsProductsResponse,
  AnalyticsRecurringResponse,
  AnalyticsTaxResponse,
  AnalyticsTrendsResponse,
  getAnalyticsAnomalies,
  getAnalyticsCalendar,
  getAnalyticsCategories,
  getAnalyticsDiagnostics,
  getAnalyticsForecast,
  getAnalyticsInsightFeed,
  getAnalyticsMerchants,
  getAnalyticsProducts,
  getAnalyticsRecurring,
  getAnalyticsTax,
  getAnalyticsTrends,
} from "@/lib/analytics-api";
import type { CategoryBreakdown, RangePreset } from "@/lib/dashboard-api";
import { RANGE_LABELS, RANGE_PRESETS } from "@/lib/dashboard-api";
import type { Insight } from "@/lib/insights-api";
import { Badge, Button, Card, PillTab } from "@/components/ui";

const TABS = [
  { key: "overview", label: "Tổng quan" },
  { key: "categories", label: "Danh mục" },
  { key: "cashflow", label: "Dòng tiền" },
  { key: "documents", label: "Chứng từ & VAT" },
  { key: "advice", label: "Gợi ý" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

type AnalyticsState = {
  categories: CategoryBreakdown[];
  trends: AnalyticsTrendsResponse;
  merchants: AnalyticsMerchantsResponse;
  anomalies: AnalyticsAnomaliesResponse;
  insights: Insight[];
  products: AnalyticsProductsResponse;
  tax: AnalyticsTaxResponse;
  diagnostics: AnalyticsDiagnosticsResponse;
  forecast: AnalyticsForecastResponse;
  calendar: AnalyticsCalendarResponse;
  recurring: AnalyticsRecurringResponse;
};

function formatMoney(value: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return value;
  return `${amount.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} VND`;
}

function formatDate(value: string): string {
  const [y, m, d] = value.split("-");
  return y && m && d ? `${d}/${m}/${y}` : value;
}

function maxAmount(values: string[]): number {
  return Math.max(1, ...values.map((value) => Number(value) || 0));
}

function sumAmounts(values: string[]): number {
  return values.reduce((sum, value) => sum + (Number(value) || 0), 0);
}

function categoryIcon(name: string): LucideIcon {
  const normalized = name.toLowerCase();
  if (normalized.includes("ăn") || normalized.includes("cafe") || normalized.includes("coffee")) return Coffee;
  if (normalized.includes("mua") || normalized.includes("shopping")) return ShoppingBag;
  if (normalized.includes("hóa đơn") || normalized.includes("bill")) return FileText;
  if (normalized.includes("di chuyển") || normalized.includes("grab") || normalized.includes("taxi")) return Car;
  if (normalized.includes("sức khỏe") || normalized.includes("health")) return HeartPulse;
  if (normalized.includes("giải trí") || normalized.includes("game")) return Gamepad2;
  return Sparkles;
}

export default function AnalyticsClient() {
  const router = useRouter();
  const [authReady, setAuthReady] = useState(false);
  const [range, setRange] = useState<RangePreset>("30d");
  const [tab, setTab] = useState<TabKey>("overview");
  const [data, setData] = useState<AnalyticsState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await getMe();
        if (!cancelled) setAuthReady(true);
      } catch {
        router.replace("/login?next=/analytics");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [categories, trends, merchants, anomalies, insightFeed, products, tax, diagnostics, forecast, calendar, recurring] = await Promise.all([
        getAnalyticsCategories({ range, limit: 8 }),
        getAnalyticsTrends({ range, group_by: range === "30d" ? "week" : "day" }),
        getAnalyticsMerchants({ range, limit: 8 }),
        getAnalyticsAnomalies({ range, limit: 6 }),
        getAnalyticsInsightFeed({ range, limit: 4, auto_generate: true }),
        getAnalyticsProducts({ range, limit: 8 }),
        getAnalyticsTax({ range, sellers_limit: 6 }),
        getAnalyticsDiagnostics({ range, top_drivers: 5 }),
        getAnalyticsForecast(),
        getAnalyticsCalendar({ range }),
        getAnalyticsRecurring({ lookback_months: 6 }),
      ]);
      setData({
        categories: categories.items,
        trends,
        merchants,
        anomalies,
        insights: insightFeed.insights,
        products,
        tax,
        diagnostics,
        forecast,
        calendar,
        recurring,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tải dữ liệu phân tích");
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    if (authReady) void load();
  }, [authReady, load]);

  const trendMax = useMemo(() => maxAmount(data?.trends.points.map((p) => p.amount) ?? []), [data]);
  const merchantMax = useMemo(() => maxAmount(data?.merchants.items.map((m) => m.total_amount) ?? []), [data]);
  const stats = useMemo(() => {
    if (!data) {
      return {
        spend: 0, transactions: 0, topCategory: "-", topCategoryPct: 0,
        topMerchant: "-", anomalies: 0,
        budgetPercent: null as number | null, budgetStatus: "-" as string,
      };
    }
    const spend = sumAmounts(data.trends.points.map((point) => point.amount));
    // Mức dùng ngân sách: từ forecast budgets (spent / budget tổng).
    const totalBudget = data.forecast.budgets.reduce((s, b) => s + (Number(b.budget_amount) || 0), 0);
    const totalSpentBudgeted = data.forecast.budgets.reduce((s, b) => s + (Number(b.spent_so_far) || 0), 0);
    const budgetPercent = totalBudget > 0 ? Math.round((totalSpentBudgeted / totalBudget) * 100) : null;
    const exceeded = data.forecast.budgets.some((b) => b.status === "exceeded");
    const willExceed = data.forecast.budgets.some((b) => b.status === "will_exceed");
    const budgetStatus = budgetPercent === null
      ? "Chưa đặt ngân sách"
      : exceeded ? "Đã vượt ngân sách"
      : willExceed ? "Dự báo vượt"
      : budgetPercent >= 80 ? "Cần chú ý"
      : "Đúng kế hoạch";
    return {
      spend,
      transactions: data.trends.points.reduce((sum, point) => sum + point.transaction_count, 0),
      topCategory: data.categories[0]?.name ?? "-",
      topCategoryPct: data.categories[0]?.percentage ?? 0,
      topMerchant: data.merchants.items[0]?.merchant_name ?? "-",
      anomalies: data.anomalies.anomalies.length,
      budgetPercent,
      budgetStatus,
    };
  }, [data]);

  // Insight summary banner — ngôn ngữ tự nhiên, ghép từ số liệu deterministic.
  const summaryText = useMemo(() => {
    if (!data) return "";
    const parts: string[] = [];
    parts.push(`Trong kỳ này bạn đã chi ${formatMoney(String(stats.spend))} với ${stats.transactions} giao dịch.`);
    if (stats.topCategory !== "-") {
      parts.push(`${stats.topCategory} là nhóm chi lớn nhất, chiếm ${stats.topCategoryPct.toFixed(1)}%.`);
    }
    if (stats.anomalies > 0) {
      parts.push(`Có ${stats.anomalies} giao dịch cần kiểm tra.`);
    }
    const nearBudget = data.forecast.budgets
      .filter((b) => b.status === "will_exceed" || b.status === "exceeded" || b.projected_percent >= 80)
      .map((b) => b.category_name);
    if (nearBudget.length > 0) {
      parts.push(`Nhóm gần/đã chạm ngân sách: ${nearBudget.slice(0, 3).join(", ")}.`);
    }
    return parts.join(" ");
  }, [data, stats]);

  if (!authReady) {
    return <p className="text-body-sm text-mute">Đang kiểm tra phiên đăng nhập...</p>;
  }

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <h1 className="text-xl font-bold tracking-tight text-ink">Phân tích chi tiết tiêu dùng</h1>
            <p className="mt-0.5 text-sm text-ash">
              Báo cáo phân bổ dòng tiền chi tiêu theo từng nhóm danh mục cụ thể.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {RANGE_PRESETS.filter((item) => item !== "custom").map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setRange(item)}
                className={`rounded-lg border px-3 py-2 text-button-sm transition-colors ${
                  range === item
                    ? "border-ink bg-ink text-on-dark"
                    : "border-hairline-soft bg-surface-doc text-body hover:text-ink"
                }`}
              >
                {RANGE_LABELS[item]}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <AnalyticsStat icon={TrendingDown} label="Tổng chi tiêu" value={formatMoney(String(stats.spend))} detail="Theo giao dịch đã ghi sổ" tone="red" />
          <AnalyticsStat icon={Activity} label="Tần suất giao dịch" value={`${stats.transactions} giao dịch`} detail="Trong kỳ đang xem" tone="neutral" />
          <AnalyticsStat icon={PieChart} label="Danh mục nổi bật" value={stats.topCategory} detail="Chiếm tỷ trọng cao nhất" tone="green" />
          <AnalyticsStat icon={Store} label="Cửa hàng nổi bật" value={stats.topMerchant} detail="Phát sinh nhiều nhất" tone="blue" />
          <AnalyticsStat icon={ArrowUpRight} label="Bất thường" value={String(stats.anomalies)} detail="Cần kiểm tra" tone="purple" />
        </div>
      </header>

      {error && (
        <div className="rounded-md border border-accent-red bg-accent-red-soft p-4 text-body-sm text-accent-red">
          {error}
        </div>
      )}

      {loading && <Card>Đang tải dữ liệu phân tích...</Card>}

      {data && !loading && (
        <div className="grid gap-4 lg:grid-cols-12">
          <section className="lg:col-span-8 space-y-4">
            <Card className="space-y-4 border-hairline-soft bg-surface-card">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
                    <Calendar className="h-4 w-4 text-mute" aria-hidden />
                    Biểu đồ phân phối chi phí theo thời gian
                  </h2>
                  <p className="text-caption-sm text-mute">Theo {data.trends.group_by === "week" ? "tuần" : "ngày"}</p>
                </div>
                <Badge tone="blue">{data.trends.points.length} điểm</Badge>
              </div>
              <div className="flex h-56 items-stretch gap-2 border-b border-hairline-soft pb-3">
                {data.trends.points.length === 0 ? (
                  <p className="self-center text-body-sm text-mute">Chưa có giao dịch trong kỳ này.</p>
                ) : (
                  data.trends.points.map((point) => {
                    const height = Math.max(2, ((Number(point.amount) || 0) / trendMax) * 100);
                    return (
                      <div key={`${point.period_start}-${point.period_end}`} className="flex min-w-8 flex-1 flex-col items-center justify-end gap-2">
                        <div className="flex w-full flex-1 items-end">
                          <div className="w-full rounded-sm bg-accent-blue transition-all" style={{ height: `${height}%` }} title={formatMoney(point.amount)} />
                        </div>
                        <span className="text-[11px] text-mute">{formatDate(point.period_start).slice(0, 5)}</span>
                      </div>
                    );
                  })
                )}
              </div>
            </Card>

            <Card className="space-y-4 border-hairline-soft bg-surface-card">
              <div className="flex items-center justify-between gap-3">
                <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
                  <PieChart className="h-4 w-4 text-mute" aria-hidden />
                  Biểu đồ phân phối chi phí danh mục
                </h2>
                <Link href="/budgets" className="text-button-sm text-accent-green hover:underline">Quản lý ngân sách</Link>
              </div>
              <div className="space-y-3">
                {data.categories.map((category) => {
                  const Icon = categoryIcon(category.name);
                  return (
                  <div key={`${category.category_id}-${category.name}`} className="space-y-1 rounded-lg border border-hairline-soft bg-surface-doc p-3">
                    <div className="flex justify-between gap-3 text-body-sm">
                      <span className="flex min-w-0 items-center gap-2 font-semibold text-ink">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white text-mute">
                          <Icon className="h-4 w-4" aria-hidden />
                        </span>
                        <span className="truncate">{category.name}</span>
                      </span>
                      <span className="shrink-0 text-mute">{formatMoney(category.total_amount)}</span>
                    </div>
                    <div className="h-2 rounded-full bg-surface-soft">
                      <div className="h-full rounded-full bg-accent-green" style={{ width: `${Math.min(100, category.percentage)}%` }} />
                    </div>
                  </div>
                );})}
                {data.categories.length === 0 && <p className="text-body-sm text-mute">Chưa có dữ liệu danh mục.</p>}
              </div>
            </Card>

            <DiagnosticsCard data={data.diagnostics} />

            <CalendarHeatmapCard data={data.calendar} />

            <ProductsCard data={data.products} />

            <TaxCard data={data.tax} />
          </section>

          <aside className="lg:col-span-4 space-y-4">
            <ForecastCard data={data.forecast} />

            <RecurringCard data={data.recurring} />

            <Card className="space-y-4 border-hairline-soft bg-surface-card">
              <h2 className="text-heading-sm-mixed text-ink">Cửa hàng nổi bật</h2>
              <div className="space-y-3">
                {data.merchants.items.map((merchant) => {
                  const width = ((Number(merchant.total_amount) || 0) / merchantMax) * 100;
                  return (
                    <div key={merchant.merchant_name} className="space-y-1">
                      <div className="flex justify-between gap-3 text-caption-sm">
                        <span className="truncate text-ink">{merchant.merchant_name}</span>
                        <span className="text-mute">{formatMoney(merchant.total_amount)}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-surface-soft">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(4, width)}%` }} />
                      </div>
                    </div>
                  );
                })}
                {data.merchants.items.length === 0 && <p className="text-body-sm text-mute">Chưa có merchant.</p>}
              </div>
            </Card>

            <Card className="space-y-3 border-hairline-soft bg-surface-card">
              <h2 className="text-heading-sm-mixed text-ink">Gợi ý cần xem lại</h2>
              {data.anomalies.anomalies.map((item) => (
                <Link key={item.id} href={`/transactions/${item.transaction_id}`} className="block rounded-md border border-hairline-soft p-3 hover:bg-surface-soft">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-caption-md text-ink">{item.title}</span>
                    <Badge tone={item.severity === "danger" ? "red" : "purple"}>{item.severity}</Badge>
                  </div>
                  <p className="mt-1 text-caption-sm text-mute">{item.reason}</p>
                </Link>
              ))}
              {data.anomalies.anomalies.length === 0 && <p className="text-body-sm text-mute">Không có bất thường nổi bật.</p>}
            </Card>

            <Card className="space-y-3 border-hairline-soft bg-surface-card">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-heading-sm-mixed text-ink">Insight nhanh</h2>
                <Link href="/insights" className="text-button-sm text-accent-green hover:underline">Mở</Link>
              </div>
              {data.insights.map((insight) => (
                <div key={insight.id} className="border-b border-hairline-soft pb-3 last:border-0 last:pb-0">
                  <Badge tone={insight.severity === "danger" || insight.severity === "warning" ? "red" : "green"}>{insight.severity}</Badge>
                  <p className="mt-2 text-caption-md text-ink">{insight.title}</p>
                  <p className="mt-1 text-caption-sm text-mute">{insight.summary}</p>
                </div>
              ))}
              {data.insights.length === 0 && <p className="text-body-sm text-mute">Chưa có insight.</p>}
            </Card>
          </aside>
        </div>
      )}

      <div className="flex justify-end">
        <Button variant="secondary" onClick={() => void load()}>Làm mới phân tích</Button>
      </div>
    </div>
  );
}

function AnalyticsStat({ icon: Icon, label, value, detail, tone }: { icon: LucideIcon; label: string; value: string; detail: string; tone: "neutral" | "red" | "green" | "blue" | "purple" }) {
  const toneClass = {
    neutral: "bg-surface-doc text-ink",
    red: "bg-accent-red-soft text-accent-red",
    green: "bg-accent-green-soft text-accent-green",
    blue: "bg-accent-blue-soft text-link-blue",
    purple: "bg-accent-purple-soft text-accent-purple",
  }[tone];
  return (
    <article className="rounded-xl border border-hairline-soft bg-white p-4 transition-all hover:shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">{label}</p>
          <p className="mt-2 truncate text-xl font-black text-ink">{value}</p>
        </div>
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${toneClass}`}>
          <Icon className="h-4.5 w-4.5" aria-hidden />
        </span>
      </div>
      <p className="mt-2 text-caption-sm text-mute">{detail}</p>
    </article>
  );
}

const FORECAST_STATUS: Record<string, { label: string; tone: "green" | "red" | "purple" | "blue" }> = {
  on_track: { label: "Đúng kế hoạch", tone: "green" },
  warning: { label: "Cần chú ý", tone: "purple" },
  will_exceed: { label: "Dự báo vượt", tone: "red" },
  exceeded: { label: "Đã vượt", tone: "red" },
};

function ForecastCard({ data }: { data: import("@/lib/analytics-api").AnalyticsForecastResponse }) {
  const { month, budgets } = data;
  const spent = Number(month.spent_so_far) || 0;
  const projected = Number(month.projected_total) || 0;
  const progress = projected > 0 ? Math.min(100, (spent / projected) * 100) : 0;
  return (
    <Card className="space-y-4 border-hairline-soft bg-surface-card">
      <div>
        <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
          <TrendingUp className="h-4 w-4 text-mute" aria-hidden />
          Dự báo cuối tháng
        </h2>
        <p className="text-caption-sm text-mute">
          Tháng {month.period_month} · {month.days_elapsed}/{month.days_in_month} ngày
        </p>
      </div>
      {spent === 0 ? (
        <p className="text-body-sm text-mute">Chưa có giao dịch nào trong tháng này để dự báo.</p>
      ) : (
        <>
          <div className="space-y-1">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-caption-sm text-mute">Đã chi</span>
              <span className="text-body-strong text-ink">{formatMoney(month.spent_so_far)}</span>
            </div>
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-caption-sm text-mute">Dự kiến cả tháng</span>
              <span className="text-body-strong text-accent-blue">{formatMoney(month.projected_total)}</span>
            </div>
            <div className="mt-2 h-2 rounded-full bg-surface-soft">
              <div className="h-full rounded-full bg-accent-blue" style={{ width: `${progress}%` }} />
            </div>
            <p className="text-caption-sm text-mute">Nhịp chi ~{formatMoney(month.daily_run_rate)}/ngày</p>
          </div>
          {budgets.length > 0 && (
            <div className="space-y-2 border-t border-hairline-soft pt-3">
              <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Ngân sách dự báo</p>
              {budgets.map((b) => {
                const status = FORECAST_STATUS[b.status] ?? FORECAST_STATUS.on_track;
                return (
                  <div key={b.category_id} className="space-y-1">
                    <div className="flex justify-between gap-2 text-caption-sm">
                      <span className="truncate text-ink">{b.category_name}</span>
                      <Badge tone={status.tone}>{status.label}</Badge>
                    </div>
                    <div className="flex justify-between gap-2 text-caption-sm text-mute">
                      <span>Dự kiến {formatMoney(b.projected_spend)} / {formatMoney(b.budget_amount)}</span>
                      <span>{b.projected_percent.toFixed(0)}%</span>
                    </div>
                    {b.projected_exceed_date && (
                      <p className="text-caption-sm text-accent-red">Dự kiến chạm hạn mức ngày {formatDate(b.projected_exceed_date)}</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </Card>
  );
}

function DiagnosticsCard({ data }: { data: import("@/lib/analytics-api").AnalyticsDiagnosticsResponse }) {
  const delta = Number(data.delta_amount) || 0;
  const up = delta > 0;
  const hasPrev = Number(data.previous_total) > 0;
  return (
    <Card className="space-y-4 border-hairline-soft bg-surface-card">
      <div className="flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
          <Activity className="h-4 w-4 text-mute" aria-hidden />
          Vì sao chi tiêu thay đổi
        </h2>
        {hasPrev && (
          <span className={`flex items-center gap-1 text-body-sm font-semibold ${up ? "text-accent-red" : "text-accent-green"}`}>
            {up ? <ArrowUpRight className="h-4 w-4" aria-hidden /> : <ArrowDownRight className="h-4 w-4" aria-hidden />}
            {formatMoney(String(Math.abs(delta)))}
            {data.delta_percent !== null && ` (${Math.abs(data.delta_percent).toFixed(0)}%)`}
          </span>
        )}
      </div>
      {!hasPrev ? (
        <p className="text-body-sm text-mute">Chưa đủ dữ liệu kỳ trước để so sánh.</p>
      ) : data.drivers.length === 0 ? (
        <p className="text-body-sm text-mute">Không có thay đổi đáng kể giữa hai kỳ.</p>
      ) : (
        <div className="space-y-3">
          {data.drivers.map((driver) => {
            const dUp = driver.direction === "increase";
            return (
              <div key={`${driver.category_id}-${driver.category_name}`} className="rounded-lg border border-hairline-soft bg-surface-doc p-3">
                <div className="flex justify-between gap-3 text-body-sm">
                  <span className="font-semibold text-ink">{driver.category_name}</span>
                  <span className={`flex items-center gap-1 font-semibold ${dUp ? "text-accent-red" : "text-accent-green"}`}>
                    {dUp ? "+" : "−"}{formatMoney(String(Math.abs(Number(driver.delta_amount) || 0)))}
                  </span>
                </div>
                {driver.top_merchants.length > 0 && (
                  <p className="mt-1 text-caption-sm text-mute">
                    {driver.top_merchants.slice(0, 2).map((m) => m.merchant_name).join(", ")}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function ProductsCard({ data }: { data: import("@/lib/analytics-api").AnalyticsProductsResponse }) {
  return (
    <Card className="space-y-4 border-hairline-soft bg-surface-card">
      <div>
        <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
          <ShoppingBag className="h-4 w-4 text-mute" aria-hidden />
          Top sản phẩm / món
        </h2>
        <p className="text-caption-sm text-mute">Dựa trên hóa đơn OCR đã xác nhận</p>
      </div>
      {data.items.length === 0 ? (
        <p className="text-body-sm text-mute">Chưa có dữ liệu sản phẩm. Hãy tải hóa đơn lên để bóc tách chi tiết món.</p>
      ) : (
        <div className="space-y-2">
          {data.items.map((p) => (
            <div key={p.item_name} className="space-y-1 rounded-lg border border-hairline-soft bg-surface-doc p-3">
              <div className="flex justify-between gap-3 text-body-sm">
                <span className="min-w-0 truncate font-medium text-ink">{p.item_name}</span>
                <span className="shrink-0 text-mute">{formatMoney(p.total_amount)}</span>
              </div>
              <div className="flex items-center justify-between gap-2 text-caption-sm text-mute">
                <span>SL {Number(p.total_quantity).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} · {p.line_count} dòng</span>
                <span>{p.percentage.toFixed(0)}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-surface-soft">
                <div className="h-full rounded-full bg-accent-green" style={{ width: `${Math.min(100, p.percentage)}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function TaxCard({ data }: { data: import("@/lib/analytics-api").AnalyticsTaxResponse }) {
  if (data.invoice_count === 0) {
    return (
      <Card className="space-y-4 border-hairline-soft bg-surface-card">
        <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
          <Receipt className="h-4 w-4 text-mute" aria-hidden />
          VAT &amp; người bán
        </h2>
        <p className="text-body-sm text-mute">Chưa có hóa đơn VAT trong kỳ này.</p>
      </Card>
    );
  }
  return (
    <Card className="space-y-4 border-hairline-soft bg-surface-card">
      <div>
        <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
          <Receipt className="h-4 w-4 text-mute" aria-hidden />
          VAT &amp; người bán
        </h2>
        <p className="text-caption-sm text-mute">{data.invoice_count} hóa đơn · thuế suất hiệu dụng {data.effective_tax_rate.toFixed(1)}%</p>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <TaxStat label="Trước thuế" value={formatMoney(data.subtotal_before_tax)} />
        <TaxStat label="Thuế VAT" value={formatMoney(data.total_tax)} />
        <TaxStat label="Tổng cộng" value={formatMoney(data.grand_total)} />
      </div>
      {data.top_sellers.length > 0 && (
        <div className="space-y-2 border-t border-hairline-soft pt-3">
          <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Người bán nổi bật</p>
          {data.top_sellers.map((s) => (
            <div key={`${s.seller_name}-${s.seller_tax_id ?? ""}`} className="flex justify-between gap-3 text-caption-sm">
              <span className="min-w-0 truncate text-ink">
                {s.seller_name}
                {s.seller_tax_id && <span className="ml-1 text-mute">· MST {s.seller_tax_id}</span>}
              </span>
              <span className="shrink-0 text-mute">{formatMoney(s.total_amount)}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function TaxStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-hairline-soft bg-surface-doc p-3">
      <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">{label}</p>
      <p className="mt-1 truncate text-body-strong text-ink" title={value}>{value}</p>
    </div>
  );
}

const HEAT_COLORS = [
  "bg-surface-soft",        // 0 - no spend
  "bg-accent-green-soft",   // 1 - low
  "bg-accent-blue-soft",    // 2 - medium
  "bg-accent-blue",         // 3 - high
  "bg-accent-red",          // 4 - unusual
];

const WEEKDAY_LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

function CalendarHeatmapCard({ data }: { data: import("@/lib/analytics-api").AnalyticsCalendarResponse }) {
  // Map ngày -> dữ liệu để tra cứu nhanh.
  const byDate = new Map(data.days.map((d) => [d.date, d]));
  const total = data.days.reduce((sum, d) => sum + (Number(d.amount) || 0), 0);

  if (data.days.length === 0) {
    return (
      <Card className="space-y-4 border-hairline-soft bg-surface-card">
        <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
          <Calendar className="h-4 w-4 text-mute" aria-hidden />
          Lịch nhiệt chi tiêu
        </h2>
        <p className="text-body-sm text-mute">Chưa có giao dịch trong kỳ này.</p>
      </Card>
    );
  }

  // Dựng các cột tuần từ start -> end. Mỗi cột 7 ô (T2..CN).
  const start = new Date(`${data.range.start}T00:00:00`);
  const end = new Date(`${data.range.end}T00:00:00`);
  // Lùi start về thứ Hai của tuần chứa nó.
  const startMonday = new Date(start);
  const startDow = (start.getDay() + 6) % 7; // 0=Mon..6=Sun
  startMonday.setDate(start.getDate() - startDow);

  const weeks: Array<Array<{ iso: string; inRange: boolean } | null>> = [];
  const cursor = new Date(startMonday);
  while (cursor <= end) {
    const week: Array<{ iso: string; inRange: boolean } | null> = [];
    for (let i = 0; i < 7; i += 1) {
      const iso = `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, "0")}-${String(cursor.getDate()).padStart(2, "0")}`;
      const inRange = cursor >= start && cursor <= end;
      week.push({ iso, inRange });
      cursor.setDate(cursor.getDate() + 1);
    }
    weeks.push(week);
  }

  return (
    <Card className="space-y-4 border-hairline-soft bg-surface-card">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
            <Calendar className="h-4 w-4 text-mute" aria-hidden />
            Lịch nhiệt chi tiêu
          </h2>
          <p className="text-caption-sm text-mute">Tổng {formatMoney(String(total))} trong kỳ</p>
        </div>
      </div>
      <div className="overflow-x-auto">
        <div className="flex gap-2">
          <div className="flex flex-col justify-between py-0.5 pr-1 text-[10px] text-mute">
            {WEEKDAY_LABELS.map((label) => (
              <span key={label} className="h-3.5 leading-3.5">{label}</span>
            ))}
          </div>
          <div className="flex gap-1">
            {weeks.map((week, wi) => (
              <div key={wi} className="flex flex-col gap-1">
                {week.map((cell, di) => {
                  if (!cell || !cell.inRange) {
                    return <div key={di} className="h-3.5 w-3.5 rounded-sm bg-transparent" />;
                  }
                  const day = byDate.get(cell.iso);
                  const intensity = day ? day.intensity : 0;
                  const color = HEAT_COLORS[intensity] ?? HEAT_COLORS[0];
                  const title = day
                    ? `${formatDate(cell.iso)}: ${formatMoney(day.amount)} (${day.transaction_count} giao dịch)${day.is_unusual ? " · bất thường" : ""}`
                    : `${formatDate(cell.iso)}: không chi`;
                  return <div key={di} className={`h-3.5 w-3.5 rounded-sm ${color}`} title={title} />;
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 text-[10px] text-mute">
        <span>Ít</span>
        {HEAT_COLORS.map((c) => (
          <span key={c} className={`h-3 w-3 rounded-sm ${c}`} />
        ))}
        <span>Nhiều</span>
      </div>
    </Card>
  );
}

function RecurringCard({ data }: { data: import("@/lib/analytics-api").AnalyticsRecurringResponse }) {
  const fixed = Number(data.fixed_monthly_estimate) || 0;
  const variable = Number(data.variable_last_month) || 0;
  const total = fixed + variable;
  const fixedPct = total > 0 ? (fixed / total) * 100 : 0;
  return (
    <Card className="space-y-4 border-hairline-soft bg-surface-card">
      <div>
        <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
          <Activity className="h-4 w-4 text-mute" aria-hidden />
          Chi cố định vs biến đổi
        </h2>
        <p className="text-caption-sm text-mute">Ước tính từ {data.lookback_months} tháng gần nhất</p>
      </div>
      {data.recurring_items.length === 0 ? (
        <p className="text-body-sm text-mute">Chưa phát hiện khoản chi định kỳ nào.</p>
      ) : (
        <>
          <div className="space-y-1">
            <div className="flex h-2.5 overflow-hidden rounded-full bg-surface-soft">
              <div className="h-full bg-accent-blue" style={{ width: `${fixedPct}%` }} title="Cố định" />
              <div className="h-full bg-accent-green" style={{ width: `${100 - fixedPct}%` }} title="Biến đổi" />
            </div>
            <div className="flex justify-between gap-2 text-caption-sm">
              <span className="text-accent-blue">Cố định ~{formatMoney(data.fixed_monthly_estimate)}/tháng</span>
              <span className="text-accent-green">Biến đổi {formatMoney(data.variable_last_month)}</span>
            </div>
          </div>
          <div className="space-y-2 border-t border-hairline-soft pt-3">
            <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Khoản định kỳ</p>
            {data.recurring_items.slice(0, 6).map((item) => (
              <div key={item.merchant_name} className="flex justify-between gap-3 text-caption-sm">
                <span className="min-w-0 truncate text-ink">
                  {item.merchant_name}
                  <span className="ml-1 text-mute">· {item.months_active} tháng</span>
                </span>
                <span className="shrink-0 text-mute">~{formatMoney(item.avg_monthly_amount)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
