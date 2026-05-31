"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  Calendar,
  Car,
  Coffee,
  FileText,
  Gamepad2,
  HeartPulse,
  PieChart,
  ShoppingBag,
  Sparkles,
  Store,
  TrendingDown,
  type LucideIcon,
} from "lucide-react";

import { getMe } from "@/lib/auth-api";
import {
  AnalyticsAnomaliesResponse,
  AnalyticsMerchantsResponse,
  AnalyticsTrendsResponse,
  getAnalyticsAnomalies,
  getAnalyticsCategories,
  getAnalyticsInsightFeed,
  getAnalyticsMerchants,
  getAnalyticsTrends,
} from "@/lib/analytics-api";
import type { CategoryBreakdown, RangePreset } from "@/lib/dashboard-api";
import { RANGE_LABELS, RANGE_PRESETS } from "@/lib/dashboard-api";
import type { Insight } from "@/lib/insights-api";
import { Badge, Button, Card } from "@/components/ui";

type AnalyticsState = {
  categories: CategoryBreakdown[];
  trends: AnalyticsTrendsResponse;
  merchants: AnalyticsMerchantsResponse;
  anomalies: AnalyticsAnomaliesResponse;
  insights: Insight[];
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
      const [categories, trends, merchants, anomalies, insightFeed] = await Promise.all([
        getAnalyticsCategories({ range, limit: 8 }),
        getAnalyticsTrends({ range, group_by: range === "30d" ? "week" : "day" }),
        getAnalyticsMerchants({ range, limit: 8 }),
        getAnalyticsAnomalies({ range, limit: 6 }),
        getAnalyticsInsightFeed({ range, limit: 4, auto_generate: true }),
      ]);
      setData({
        categories: categories.items,
        trends,
        merchants,
        anomalies,
        insights: insightFeed.insights,
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
      return { spend: 0, transactions: 0, topCategory: "-", topMerchant: "-", anomalies: 0 };
    }
    return {
      spend: sumAmounts(data.trends.points.map((point) => point.amount)),
      transactions: data.trends.points.reduce((sum, point) => sum + point.transaction_count, 0),
      topCategory: data.categories[0]?.name ?? "-",
      topMerchant: data.merchants.items[0]?.merchant_name ?? "-",
      anomalies: data.anomalies.anomalies.length,
    };
  }, [data]);

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
          </section>

          <aside className="lg:col-span-4 space-y-4">
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
