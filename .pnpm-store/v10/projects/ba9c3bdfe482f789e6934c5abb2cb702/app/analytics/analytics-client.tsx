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
import type { CategoryBreakdown, RangeInfo, RangePreset } from "@/lib/dashboard-api";
import type { Insight } from "@/lib/insights-api";
import { Badge, Button, Card, PillTab } from "@/components/ui";
import { categoryColor } from "@/lib/chart-colors";
import {
  CategoryDonut,
  HorizontalBarChart,
  TrendAreaChart,
  type DonutDatum,
  type HBarDatum,
} from "./analytics-charts";

const TABS = [
  { key: "overview", label: "Tổng quan" },
  { key: "categories", label: "Danh mục" },
  { key: "cashflow", label: "Dòng tiền" },
  { key: "documents", label: "Chứng từ & VAT" },
  { key: "advice", label: "Gợi ý" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

type SectionKey =
  | "categories" | "trends" | "merchants" | "anomalies" | "insights"
  | "products" | "tax" | "diagnostics" | "forecast" | "calendar" | "recurring";

type PromiseSettledStatus = "fulfilled" | "rejected";

function emptyRange(preset: RangePreset): RangeInfo {
  const today = new Date();
  const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return { preset, start: iso(today), end: iso(today), days: 1 };
}

const MONTH_NAMES = [
  "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
  "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12",
];

/** 12 tháng gần nhất (kể cả tháng hiện tại) cho dropdown chọn tháng. */
function recentMonths(count = 12): Array<{ value: string; label: string }> {
  const out: Array<{ value: string; label: string }> = [];
  const today = new Date();
  for (let i = 0; i < count; i += 1) {
    const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    out.push({ value, label: `${MONTH_NAMES[d.getMonth()]}/${d.getFullYear()}` });
  }
  return out;
}

/** Biên đầu/cuối của 1 tháng "YYYY-MM" dưới dạng ISO date. */
function monthBounds(ym: string): { start: string; end: string } {
  const [y, m] = ym.split("-").map(Number);
  const lastDay = new Date(y, m, 0).getDate();
  return { start: `${ym}-01`, end: `${ym}-${String(lastDay).padStart(2, "0")}` };
}

/** Tham số custom range đúng tên API: start_date / end_date. */
function monthBoundsParams(ym: string): { start_date: string; end_date: string } {
  const { start, end } = monthBounds(ym);
  return { start_date: start, end_date: end };
}

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

function currentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function AnalyticsClient() {
  const router = useRouter();
  const [authReady, setAuthReady] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState<string>(currentMonth());
  const [tab, setTab] = useState<TabKey>("overview");
  const [data, setData] = useState<AnalyticsState | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState<Set<SectionKey>>(new Set());
  const [fatalError, setFatalError] = useState<string | null>(null);

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
    setFatalError(null);
    const range: RangePreset = "custom";
    const rangeMeta = emptyRange(range);
    const q = { range, ...monthBoundsParams(selectedMonth) };
    const groupBy = "day";
    const results = await Promise.allSettled([
      getAnalyticsCategories({ ...q, limit: 8 }),
      getAnalyticsTrends({ ...q, group_by: groupBy }),
      getAnalyticsMerchants({ ...q, limit: 8 }),
      getAnalyticsAnomalies({ ...q, limit: 6 }),
      getAnalyticsInsightFeed({ ...q, limit: 4, auto_generate: true }),
      getAnalyticsProducts({ ...q, limit: 8 }),
      getAnalyticsTax({ ...q, sellers_limit: 6 }),
      getAnalyticsDiagnostics({ ...q, top_drivers: 5 }),
      getAnalyticsForecast(),
      getAnalyticsCalendar({ ...q }),
      getAnalyticsRecurring({ lookback_months: 6 }),
    ]);
    const [categories, trends, merchants, anomalies, insightFeed, products, tax, diagnostics, forecast, calendar, recurring] = results;

    const nextFailed = new Set<SectionKey>();
    const mark = (key: SectionKey, r: PromiseSettledStatus): void => {
      if (r === "rejected") nextFailed.add(key);
    };
    mark("categories", categories.status);
    mark("trends", trends.status);
    mark("merchants", merchants.status);
    mark("anomalies", anomalies.status);
    mark("insights", insightFeed.status);
    mark("products", products.status);
    mark("tax", tax.status);
    mark("diagnostics", diagnostics.status);
    mark("forecast", forecast.status);
    mark("calendar", calendar.status);
    mark("recurring", recurring.status);

    // Nếu TẤT CẢ fail → lỗi mạng/phiên, hiện lỗi toàn trang.
    if (nextFailed.size === results.length) {
      setFatalError("Không thể tải dữ liệu phân tích. Vui lòng thử lại.");
      setLoading(false);
      return;
    }

    setData({
      categories: categories.status === "fulfilled" ? categories.value.items : [],
      trends: trends.status === "fulfilled" ? trends.value : { range: rangeMeta, group_by: "day", points: [] },
      merchants: merchants.status === "fulfilled" ? merchants.value : { range: rangeMeta, items: [] },
      anomalies: anomalies.status === "fulfilled" ? anomalies.value : { range: rangeMeta, anomalies: [] },
      insights: insightFeed.status === "fulfilled" ? insightFeed.value.insights : [],
      products: products.status === "fulfilled" ? products.value : { range: rangeMeta, items: [] },
      tax: tax.status === "fulfilled" ? tax.value : { range: rangeMeta, subtotal_before_tax: "0", total_tax: "0", grand_total: "0", invoice_count: 0, effective_tax_rate: 0, top_sellers: [] },
      diagnostics: diagnostics.status === "fulfilled" ? diagnostics.value : { range: rangeMeta, previous_range: rangeMeta, current_total: "0", previous_total: "0", delta_amount: "0", delta_percent: null, drivers: [] },
      forecast: forecast.status === "fulfilled" ? forecast.value : { month: { period_month: rangeMeta.start.slice(0, 7), days_elapsed: 0, days_in_month: 30, spent_so_far: "0", daily_run_rate: "0", projected_total: "0" }, budgets: [] },
      calendar: calendar.status === "fulfilled" ? calendar.value : { range: rangeMeta, days: [], legend: { levels: {} } },
      recurring: recurring.status === "fulfilled" ? recurring.value : { lookback_months: 6, fixed_monthly_estimate: "0", variable_last_month: "0", recurring_items: [] },
    });
    setFailed(nextFailed);
    setLoading(false);
  }, [selectedMonth]);

  useEffect(() => {
    if (authReady) void load();
  }, [authReady, load]);

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

  const rangeWindow = data ? `${formatDate(data.trends.range.start)} – ${formatDate(data.trends.range.end)}` : "";

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <h1 className="text-xl font-bold tracking-tight text-ink">Phân tích chi tiêu</h1>
            <p className="mt-0.5 text-sm text-mute">
              Dashboard tài chính cá nhân: tổng quan, danh mục, dòng tiền, chứng từ và gợi ý.
              {rangeWindow && <span className="ml-1 font-medium text-ink">Kỳ: {rangeWindow}</span>}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              aria-label="Chọn tháng"
              className="rounded-lg border border-ink bg-ink px-4 py-2 text-button-sm font-bold text-on-dark transition-colors hover:opacity-90"
            >
              {recentMonths(12).map((m) => (
                <option key={m.value} value={m.value} className="bg-surface-card text-ink">{m.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <AnalyticsStat icon={TrendingDown} label="Tổng chi tiêu" value={formatMoney(String(stats.spend))} detail="Theo giao dịch đã ghi sổ" tone="blue" />
          <AnalyticsStat icon={Activity} label="Số giao dịch" value={`${stats.transactions} giao dịch`} detail="Trong kỳ đang xem" tone="neutral" />
          <AnalyticsStat icon={PieChart} label="Danh mục lớn nhất" value={stats.topCategory} detail={stats.topCategoryPct > 0 ? `Chiếm ${stats.topCategoryPct.toFixed(1)}% tổng chi` : "Chưa có dữ liệu"} tone="green" />
          <AnalyticsStat icon={ArrowUpRight} label="Cảnh báo" value={`${stats.anomalies} giao dịch`} detail="Cần kiểm tra" tone="red" />
          <AnalyticsStat icon={Store} label="Mức dùng ngân sách" value={stats.budgetPercent === null ? "—" : `${stats.budgetPercent}%`} detail={stats.budgetStatus} tone="purple" />
        </div>
      </header>

      {fatalError && (
        <div className="rounded-md border border-accent-red bg-accent-red-soft p-4 text-body-sm text-accent-red">
          {fatalError}
          <button type="button" className="ml-3 font-semibold underline" onClick={() => void load()}>Thử lại</button>
        </div>
      )}

      {loading && <AnalyticsSkeleton />}

      {data && !loading && !fatalError && (
        <>
          {/* Insight summary banner — ngôn ngữ tự nhiên */}
          {summaryText && (
            <div className="flex items-start gap-3 rounded-xl border border-accent-blue-soft bg-accent-blue-soft/40 p-4">
              <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-accent-blue" aria-hidden />
              <p className="text-body-sm text-ink">{summaryText}</p>
            </div>
          )}

          {/* Tab bar */}
          <div className="flex gap-1 overflow-x-auto rounded-full border border-hairline-soft bg-surface-card p-1">
            {TABS.map((t) => (
              <PillTab key={t.key} active={tab === t.key} onClick={() => setTab(t.key)}>
                {t.label}
              </PillTab>
            ))}
          </div>

          {tab === "overview" && (
            <div className="grid gap-4 lg:grid-cols-12">
              <section className="lg:col-span-8 space-y-4">
                <Section failed={failed.has("trends")} onRetry={load} title="Xu hướng chi tiêu"><TrendCard data={data} /></Section>
                <Section failed={failed.has("diagnostics")} onRetry={load} title="Vì sao chi tiêu thay đổi"><DiagnosticsCard data={data.diagnostics} /></Section>
              </section>
              <aside className="lg:col-span-4 space-y-4">
                <Section failed={failed.has("forecast")} onRetry={load} title="Dự báo cuối tháng"><ForecastCard data={data.forecast} /></Section>
                <Section failed={failed.has("anomalies")} onRetry={load} title="Giao dịch cần kiểm tra"><AnomaliesCard data={data.anomalies} /></Section>
              </aside>
            </div>
          )}

          {tab === "categories" && (
            <div className="grid gap-4 lg:grid-cols-12">
              <section className="lg:col-span-7 space-y-4">
                <Section failed={failed.has("categories")} onRetry={load} title="Phân bổ danh mục"><CategoryListCard categories={data.categories} /></Section>
              </section>
              <aside className="lg:col-span-5 space-y-4">
                <Section failed={failed.has("merchants")} onRetry={load} title="Cửa hàng nổi bật"><MerchantsCard data={data.merchants} /></Section>
              </aside>
            </div>
          )}

          {tab === "cashflow" && (
            <div className="grid gap-4 lg:grid-cols-12">
              <section className="lg:col-span-8 space-y-4">
                <Section failed={failed.has("trends")} onRetry={load} title="Xu hướng chi tiêu"><TrendCard data={data} /></Section>
                <Section failed={failed.has("calendar")} onRetry={load} title="Lịch nhiệt chi tiêu"><CalendarHeatmapCard data={data.calendar} /></Section>
              </section>
              <aside className="lg:col-span-4 space-y-4">
                <Section failed={failed.has("recurring")} onRetry={load} title="Chi cố định vs biến đổi"><RecurringCard data={data.recurring} /></Section>
              </aside>
            </div>
          )}

          {tab === "documents" && (
            <div className="grid gap-4 lg:grid-cols-12">
              <section className="lg:col-span-7 space-y-4">
                <Section failed={failed.has("products")} onRetry={load} title="Top sản phẩm / món"><ProductsCard data={data.products} /></Section>
              </section>
              <aside className="lg:col-span-5 space-y-4">
                <Section failed={failed.has("tax")} onRetry={load} title="VAT & người bán"><TaxCard data={data.tax} /></Section>
                <Section failed={failed.has("merchants")} onRetry={load} title="Cửa hàng nổi bật"><MerchantsCard data={data.merchants} /></Section>
              </aside>
            </div>
          )}

          {tab === "advice" && (
            <div className="grid gap-4 lg:grid-cols-12">
              <section className="lg:col-span-7 space-y-4">
                <Section failed={failed.has("insights")} onRetry={load} title="Gợi ý từ dữ liệu"><InsightsCard insights={data.insights} /></Section>
              </section>
              <aside className="lg:col-span-5 space-y-4">
                <Section failed={failed.has("forecast")} onRetry={load} title="Dự báo cuối tháng"><ForecastCard data={data.forecast} /></Section>
                <Section failed={failed.has("anomalies")} onRetry={load} title="Giao dịch cần kiểm tra"><AnomaliesCard data={data.anomalies} /></Section>
              </aside>
            </div>
          )}
        </>
      )}

      <div className="flex justify-end">
        <Button variant="secondary" onClick={() => void load()} disabled={loading}>Làm mới phân tích</Button>
      </div>
    </div>
  );
}

/** Bọc 1 card: nếu section fetch lỗi → hiện thông báo + nút Thử lại thay vì card. */
function Section({
  failed,
  onRetry,
  title,
  children,
}: {
  failed: boolean;
  onRetry: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!failed) return <>{children}</>;
  return (
    <Card className="space-y-3 border-accent-red/30 bg-surface-card">
      <h2 className="text-heading-sm-mixed text-ink">{title}</h2>
      <p className="text-body-sm text-mute">Không tải được phần này.</p>
      <Button variant="secondary" size="sm" onClick={onRetry}>Thử lại</Button>
    </Card>
  );
}

/** Skeleton loading khớp layout thật (KPI row + 2 cột card) để tránh layout shift. */
function AnalyticsSkeleton() {
  return (
    <div className="space-y-6" aria-hidden>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl border border-hairline-soft bg-surface-soft" />
        ))}
      </div>
      <div className="h-14 animate-pulse rounded-xl border border-hairline-soft bg-surface-soft" />
      <div className="grid gap-4 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-8">
          <div className="h-64 animate-pulse rounded-lg border border-hairline-soft bg-surface-soft" />
          <div className="h-48 animate-pulse rounded-lg border border-hairline-soft bg-surface-soft" />
        </div>
        <div className="space-y-4 lg:col-span-4">
          <div className="h-48 animate-pulse rounded-lg border border-hairline-soft bg-surface-soft" />
          <div className="h-40 animate-pulse rounded-lg border border-hairline-soft bg-surface-soft" />
        </div>
      </div>
    </div>
  );
}

/** Empty-state có icon + câu giải thích + CTA. */
function EmptyState({
  icon: Icon,
  message,
  ctaLabel,
  ctaHref,
}: {
  icon: LucideIcon;
  message: string;
  ctaLabel?: string;
  ctaHref?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-hairline bg-surface-doc px-4 py-8 text-center">
      <Icon className="h-7 w-7 text-ash" aria-hidden />
      <p className="max-w-xs text-body-sm text-mute">{message}</p>
      {ctaLabel && ctaHref && (
        <Link href={ctaHref}>
          <Button variant="secondary" size="sm">{ctaLabel}</Button>
        </Link>
      )}
    </div>
  );
}

function TrendCard({ data }: { data: AnalyticsState }) {
  return (
    <Card className="space-y-4 border-hairline-soft bg-surface-card">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
            <Calendar className="h-4 w-4 text-mute" aria-hidden />
            Xu hướng chi tiêu theo thời gian
          </h2>
          <p className="text-caption-sm text-mute">Theo {data.trends.group_by === "week" ? "tuần" : "ngày"}</p>
        </div>
        <Badge tone="blue">{data.trends.points.length} điểm</Badge>
      </div>
      {data.trends.points.length === 0 ? (
        <EmptyState icon={Calendar} message="Chưa có giao dịch trong kỳ này. Thử mở rộng khoảng thời gian hoặc thêm giao dịch." ctaLabel="Thêm giao dịch" ctaHref="/transactions/new" />
      ) : (
        <TrendAreaChart points={data.trends.points} />
      )}
    </Card>
  );
}

function CategoryListCard({ categories }: { categories: CategoryBreakdown[] }) {
  const total = categories.reduce((s, c) => s + (Number(c.total_amount) || 0), 0);
  const donutData: DonutDatum[] = categories.map((c, i) => ({
    name: c.name,
    value: Number(c.total_amount) || 0,
    color: categoryColor(c.name, c.color, i),
    percentage: c.percentage,
  }));
  return (
    <Card className="space-y-4 border-hairline-soft bg-surface-card">
      <div className="flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
          <PieChart className="h-4 w-4 text-mute" aria-hidden />
          Phân bổ chi phí theo danh mục
        </h2>
        <Link href="/budgets" className="text-button-sm text-accent-green hover:underline">Quản lý ngân sách</Link>
      </div>
      {categories.length === 0 ? (
        <EmptyState icon={PieChart} message="Chưa có dữ liệu danh mục trong kỳ này. Thử mở rộng khoảng thời gian." ctaLabel="Thêm giao dịch" ctaHref="/transactions/new" />
      ) : (
        <>
          <CategoryDonut data={donutData} total={total} />
          <div className="space-y-3 border-t border-hairline-soft pt-3">
            {categories.map((category, i) => {
              const Icon = categoryIcon(category.name);
              const color = categoryColor(category.name, category.color, i);
              return (
                <div key={`${category.category_id}-${category.name}`} className="space-y-1">
                  <div className="flex justify-between gap-3 text-body-sm">
                    <span className="flex min-w-0 items-center gap-2 font-semibold text-ink">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md" style={{ background: `${color}1a`, color }}>
                        <Icon className="h-4 w-4" aria-hidden />
                      </span>
                      <span className="truncate">{category.name}</span>
                    </span>
                    <span className="shrink-0 text-mute">{formatMoney(category.total_amount)} · {category.percentage.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-surface-soft">
                    <div className="h-full rounded-full" style={{ width: `${Math.min(100, category.percentage)}%`, background: color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </Card>
  );
}

function MerchantsCard({ data }: { data: AnalyticsMerchantsResponse }) {
  const bars: HBarDatum[] = data.items.map((m) => ({
    name: m.merchant_name,
    value: Number(m.total_amount) || 0,
  }));
  return (
    <Card className="space-y-4 border-hairline-soft bg-surface-card">
      <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
        <Store className="h-4 w-4 text-mute" aria-hidden />
        Cửa hàng nổi bật
      </h2>
      {data.items.length === 0 ? (
        <EmptyState icon={Store} message="Chưa có cửa hàng nào trong kỳ này. Thử mở rộng khoảng thời gian." />
      ) : (
        <HorizontalBarChart data={bars} maxItems={8} />
      )}
    </Card>
  );
}

function AnomaliesCard({ data }: { data: AnalyticsAnomaliesResponse }) {
  return (
    <Card className="space-y-3 border-hairline-soft bg-surface-card">
      <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
        <ArrowUpRight className="h-4 w-4 text-mute" aria-hidden />
        Giao dịch cần kiểm tra
      </h2>
      {data.anomalies.map((item) => (
        <Link key={item.id} href={`/transactions/${item.transaction_id}`} className="block rounded-md border border-hairline-soft p-3 hover:bg-surface-soft">
          <div className="flex items-center justify-between gap-2">
            <span className="text-caption-md text-ink">{item.title}</span>
            <Badge tone={item.severity === "danger" ? "red" : "purple"}>{item.severity === "danger" ? "Rủi ro" : "Cần xem"}</Badge>
          </div>
          <p className="mt-1 text-caption-sm text-mute">{item.reason}</p>
        </Link>
      ))}
      {data.anomalies.length === 0 && (
        <EmptyState icon={ArrowUpRight} message="Không có giao dịch bất thường trong kỳ này." />
      )}
    </Card>
  );
}

function InsightsCard({ insights }: { insights: Insight[] }) {
  return (
    <Card className="space-y-3 border-hairline-soft bg-surface-card">
      <div className="flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
          <Sparkles className="h-4 w-4 text-mute" aria-hidden />
          Gợi ý từ dữ liệu
        </h2>
        <Link href="/insights" className="text-button-sm text-accent-green hover:underline">Mở tất cả</Link>
      </div>
      {insights.map((insight) => (
        <div key={insight.id} className="rounded-lg border border-hairline-soft bg-surface-doc p-3">
          <Badge tone={insight.severity === "danger" || insight.severity === "warning" ? "red" : "green"}>{severityLabel(insight.severity)}</Badge>
          <p className="mt-2 text-caption-md text-ink">{insight.title}</p>
          <p className="mt-1 text-caption-sm text-mute">{insight.summary}</p>
        </div>
      ))}
      {insights.length === 0 && (
        <EmptyState icon={Sparkles} message="Chưa có gợi ý. Thêm giao dịch để nhận phân tích tự động." ctaLabel="Thêm giao dịch" ctaHref="/transactions/new" />
      )}
    </Card>
  );
}

function severityLabel(severity: string): string {
  switch (severity) {
    case "danger": return "Rủi ro";
    case "warning": return "Cảnh báo";
    case "watch": return "Cần chú ý";
    case "success": return "Tốt";
    default: return "Thông tin";
  }
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
  const bars: HBarDatum[] = data.items.map((p) => ({
    name: p.item_name,
    value: Number(p.total_amount) || 0,
  }));
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
        <EmptyState icon={ShoppingBag} message="Chưa có dữ liệu sản phẩm. Hãy tải hóa đơn lên để bóc tách chi tiết món." ctaLabel="Tải hóa đơn lên" ctaHref="/receipts/upload" />
      ) : (
        <HorizontalBarChart data={bars} maxItems={8} />
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
