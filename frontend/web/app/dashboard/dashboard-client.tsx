"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { getMe } from "@/lib/auth-api";
import {
  DashboardSummary,
  DEFAULT_RANGE_PRESET,
  PREVIOUS_RANGE_LABELS,
  RangePreset,
  RANGE_LABELS,
  RANGE_PRESETS,
  getDashboardSummary,
  isRangePreset,
} from "@/lib/dashboard-api";

import { CategoryChart } from "./category-chart";

// Khi range=custom mà user chưa chọn ngày → tự động dùng 30 ngày gần nhất
// để gọi API thử (tránh request 400 khi vừa switch tab).
function todayIso(): string {
  const now = new Date();
  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
}

function shiftIso(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + days);
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
}

function formatVnd(amount: string): string {
  const numeric = Number(amount);
  if (!Number.isFinite(numeric)) return amount;
  return numeric.toLocaleString("vi-VN", { maximumFractionDigits: 0 });
}

function formatAmount(amount: string, currency: string): string {
  const numeric = Number(amount);
  if (!Number.isFinite(numeric)) {
    return `${amount} ${currency}`;
  }
  return `${numeric.toLocaleString("vi-VN", { maximumFractionDigits: 2 })} ${currency}`;
}

function formatDate(iso: string): string {
  // 2026-04-15 → 15/04/2026
  const [y, m, d] = iso.split("-");
  if (!y || !m || !d) return iso;
  return `${d}/${m}/${y}`;
}

function formatDelta(deltaAmount: string, deltaPercent: number | null): {
  label: string;
  color: string;
  arrow: string;
} {
  const numeric = Number(deltaAmount);
  if (!Number.isFinite(numeric) || numeric === 0) {
    return { label: "Không đổi", color: "text-slate-500", arrow: "→" };
  }
  // Tăng chi tiêu = đỏ (xấu), giảm = xanh (tốt).
  const isUp = numeric > 0;
  const color = isUp ? "text-rose-600" : "text-emerald-600";
  const arrow = isUp ? "↑" : "↓";
  const sign = isUp ? "+" : "−";
  const absVnd = formatVnd(String(Math.abs(numeric)));
  if (deltaPercent === null) {
    return { label: `${sign}${absVnd} VND`, color, arrow };
  }
  const pct = Math.abs(deltaPercent).toFixed(1);
  return { label: `${sign}${absVnd} VND (${sign}${pct}%)`, color, arrow };
}

type FilterState = {
  preset: RangePreset;
  startDate: string;
  endDate: string;
};

function readFiltersFromSearch(params: URLSearchParams): FilterState {
  const presetRaw = params.get("range");
  const preset: RangePreset = isRangePreset(presetRaw) ? presetRaw : DEFAULT_RANGE_PRESET;
  return {
    preset,
    startDate: params.get("start_date") ?? "",
    endDate: params.get("end_date") ?? "",
  };
}

export function DashboardClient() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [authReady, setAuthReady] = useState(false);
  const [filters, setFilters] = useState<FilterState>(() =>
    readFiltersFromSearch(new URLSearchParams(searchParams.toString())),
  );
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Auth gate.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await getMe();
        if (!cancelled) setAuthReady(true);
      } catch {
        if (!cancelled) router.replace("/login");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  // Sync URL ↔ state khi search params đổi (vd. user click back).
  useEffect(() => {
    setFilters(readFiltersFromSearch(new URLSearchParams(searchParams.toString())));
  }, [searchParams]);

  // Build query params cho API call (custom thiếu ngày → fallback 30d auto-fill).
  const apiParams = useMemo(() => {
    if (filters.preset !== "custom") {
      return { range: filters.preset };
    }
    if (filters.startDate && filters.endDate) {
      return {
        range: "custom" as const,
        start_date: filters.startDate,
        end_date: filters.endDate,
      };
    }
    // Custom chưa nhập đủ → tránh 400, dùng 30 ngày gần nhất tạm để có dữ liệu.
    const end = todayIso();
    const start = shiftIso(end, -29);
    return { range: "custom" as const, start_date: start, end_date: end };
  }, [filters]);

  // Fetch dữ liệu khi authReady + apiParams đổi.
  const refetch = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const summary = await getDashboardSummary(apiParams);
      setData(summary);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Không thể tải dữ liệu";
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  }, [apiParams]);

  useEffect(() => {
    if (!authReady) return;
    void refetch();
  }, [authReady, refetch]);

  const onSelectPreset = (preset: RangePreset) => {
    const newFilters: FilterState = { ...filters, preset };
    if (preset !== "custom") {
      newFilters.startDate = "";
      newFilters.endDate = "";
    }
    setFilters(newFilters);
    // Sync URL.
    const next = new URLSearchParams();
    next.set("range", preset);
    if (preset === "custom" && newFilters.startDate && newFilters.endDate) {
      next.set("start_date", newFilters.startDate);
      next.set("end_date", newFilters.endDate);
    }
    router.replace(`/dashboard?${next.toString()}`);
  };

  const onSubmitCustom = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!filters.startDate || !filters.endDate) {
      setErrorMessage("Vui lòng nhập cả ngày bắt đầu và ngày kết thúc.");
      return;
    }
    if (filters.startDate > filters.endDate) {
      setErrorMessage("Ngày bắt đầu phải <= ngày kết thúc.");
      return;
    }
    const next = new URLSearchParams();
    next.set("range", "custom");
    next.set("start_date", filters.startDate);
    next.set("end_date", filters.endDate);
    router.replace(`/dashboard?${next.toString()}`);
  };

  // Auth chưa xong: render placeholder.
  if (!authReady) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-sm text-slate-600">Đang xác thực phiên đăng nhập...</p>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header + filter tabs */}
      <header className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
            <p className="text-sm text-slate-500">
              Tổng quan chi tiêu và so sánh kỳ trước
            </p>
          </div>
          <Link
            href="/transactions/new"
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            Thêm giao dịch
          </Link>
        </div>

        <nav className="flex flex-wrap gap-2" aria-label="Khoảng thời gian">
          {RANGE_PRESETS.map((preset) => {
            const active = filters.preset === preset;
            return (
              <button
                key={preset}
                type="button"
                onClick={() => onSelectPreset(preset)}
                className={
                  "rounded-full px-3 py-1.5 text-sm font-medium transition " +
                  (active
                    ? "bg-slate-900 text-white"
                    : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100")
                }
                aria-pressed={active}
              >
                {RANGE_LABELS[preset]}
              </button>
            );
          })}
        </nav>

        {filters.preset === "custom" && (
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={onSubmitCustom}
            aria-label="Khoảng tùy chỉnh"
          >
            <label className="flex flex-col text-xs font-medium text-slate-600">
              Từ ngày
              <input
                type="date"
                value={filters.startDate}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, startDate: e.target.value }))
                }
                className="mt-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              />
            </label>
            <label className="flex flex-col text-xs font-medium text-slate-600">
              Đến ngày
              <input
                type="date"
                value={filters.endDate}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, endDate: e.target.value }))
                }
                className="mt-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              />
            </label>
            <button
              type="submit"
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              Áp dụng
            </button>
          </form>
        )}
      </header>

      {/* Error banner */}
      {errorMessage && (
        <div
          className="flex items-center justify-between rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
          role="alert"
        >
          <span>{errorMessage}</span>
          <button
            type="button"
            onClick={() => void refetch()}
            className="rounded-md border border-rose-300 bg-white px-3 py-1 text-xs font-medium text-rose-700 hover:bg-rose-100"
          >
            Thử lại
          </button>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && !data && <DashboardSkeleton />}

      {/* Empty state khi đã load xong nhưng count=0 */}
      {!isLoading && data && data.current.transaction_count === 0 && (
        <EmptyState />
      )}

      {/* Data grid */}
      {data && data.current.transaction_count > 0 && (
        <DashboardContent data={data} isRefreshing={isLoading} />
      )}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4" aria-label="Đang tải dashboard">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-slate-100"
          />
        ))}
      </div>
      <div className="h-56 animate-pulse rounded-2xl border border-slate-200 bg-slate-100" />
      <div className="h-72 animate-pulse rounded-2xl border border-slate-200 bg-slate-100" />
    </div>
  );
}

function EmptyState() {
  return (
    <section className="space-y-3 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
      <h2 className="text-lg font-semibold text-slate-900">
        Chưa có giao dịch trong kỳ này
      </h2>
      <p className="mx-auto max-w-md text-sm text-slate-500">
        Bắt đầu thêm giao dịch hoặc upload biên lai để dashboard có dữ liệu phân
        tích.
      </p>
      <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
        <Link
          href="/transactions/new"
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          Thêm giao dịch thủ công
        </Link>
        <Link
          href="/receipts/upload"
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          Upload biên lai
        </Link>
      </div>
    </section>
  );
}

function DashboardContent({
  data,
  isRefreshing,
}: {
  data: DashboardSummary;
  isRefreshing: boolean;
}) {
  const delta = formatDelta(data.delta_amount, data.delta_percent);

  return (
    <section className={isRefreshing ? "space-y-6 opacity-70" : "space-y-6"}>
      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <SummaryCard
          label="Tổng chi tiêu"
          value={`${formatVnd(data.current.total_spend)} VND`}
          hint={`${data.range.days} ngày: ${formatDate(data.range.start)} → ${formatDate(data.range.end)}`}
        />
        <SummaryCard
          label="Số giao dịch"
          value={String(data.current.transaction_count)}
          hint={`Trung bình ${(data.current.transaction_count / Math.max(1, data.range.days)).toFixed(1)} / ngày`}
        />
        <SummaryCard
          label={PREVIOUS_RANGE_LABELS[data.range.preset]}
          value={
            <span className={delta.color}>
              {delta.arrow} {delta.label}
            </span>
          }
          hint={`Kỳ trước: ${formatVnd(data.previous.total_spend)} VND`}
        />
      </div>

      {/* Previous period comparison block */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <header className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">
            So sánh kỳ trước
          </h2>
          <span className="text-xs text-slate-500">
            {formatDate(data.previous_range.start)} → {formatDate(data.previous_range.end)}
          </span>
        </header>
        <PreviousPeriodCompare data={data} />
      </section>

      {/* Category chart */}
      <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <header className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">
            Phân bổ theo danh mục
          </h2>
          <span className="text-xs text-slate-500">
            {data.top_categories.length} danh mục
          </span>
        </header>
        <CategoryChart
          categories={data.top_categories}
          totalSpend={data.current.total_spend}
        />
      </section>

      {/* Top categories list */}
      <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <header className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">
            Top danh mục chi tiêu
          </h2>
          <span className="text-xs text-slate-500">
            {data.top_categories.length} danh mục
          </span>
        </header>
        <ul className="space-y-3">
          {data.top_categories.map((cat) => (
            <li key={`${cat.category_id ?? "uncat"}-${cat.name}`} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 font-medium text-slate-800">
                  <span
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ backgroundColor: cat.color ?? "#94a3b8" }}
                    aria-hidden="true"
                  />
                  {cat.name}
                  <span className="text-xs font-normal text-slate-500">
                    ({cat.transaction_count} giao dịch)
                  </span>
                </span>
                <span className="font-medium text-slate-900">
                  {formatVnd(cat.total_amount)} VND ·{" "}
                  <span className="text-slate-500">{cat.percentage.toFixed(1)}%</span>
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.min(100, Math.max(0, cat.percentage))}%`,
                    backgroundColor: cat.color ?? "#64748b",
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* Recent transactions */}
      <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <header className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">
            Giao dịch gần đây
          </h2>
          <Link
            href="/transactions"
            className="text-sm font-medium text-slate-700 hover:text-slate-900"
          >
            Xem tất cả →
          </Link>
        </header>
        <ul className="divide-y divide-slate-100">
          {data.recent_transactions.map((tx) => (
            <li key={tx.id} className="flex items-center justify-between py-3 text-sm">
              <div>
                <p className="font-medium text-slate-900">
                  {tx.merchant_name ?? "(Không có merchant)"}
                </p>
                <p className="text-xs text-slate-500">
                  {formatDate(tx.transaction_date)}
                  {tx.category_name ? ` · ${tx.category_name}` : ""}
                </p>
              </div>
              <div className="font-medium text-slate-900">
                {formatAmount(tx.amount, tx.currency)}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </section>
  );
}

function SummaryCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

function PreviousPeriodCompare({ data }: { data: DashboardSummary }) {
  const current = Number(data.current.total_spend);
  const previous = Number(data.previous.total_spend);
  // Tính chiều rộng bar relative — chuẩn hóa theo max để 2 thanh cùng scale.
  const max = Math.max(current, previous, 1);
  const currentWidth = (current / max) * 100;
  const previousWidth = (previous / max) * 100;

  const delta = formatDelta(data.delta_amount, data.delta_percent);

  return (
    <div className="space-y-4">
      {/* Bar so sánh */}
      <div className="space-y-2">
        <CompareBar
          label="Kỳ này"
          amount={current}
          width={currentWidth}
          color="bg-slate-900"
          count={data.current.transaction_count}
        />
        <CompareBar
          label="Kỳ trước"
          amount={previous}
          width={previousWidth}
          color="bg-slate-400"
          count={data.previous.transaction_count}
        />
      </div>

      {/* Tổng hợp delta */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-4 py-3 text-sm">
        <span className="text-slate-600">Chênh lệch</span>
        <span className={`font-semibold ${delta.color}`}>
          {delta.arrow} {delta.label}
        </span>
      </div>
    </div>
  );
}

function CompareBar({
  label,
  amount,
  width,
  color,
  count,
}: {
  label: string;
  amount: number;
  width: number;
  color: string;
  count: number;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-900">
          {formatVnd(String(amount))} VND
          <span className="ml-2 text-xs text-slate-500">({count} GD)</span>
        </span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.min(100, Math.max(0, width))}%` }}
        />
      </div>
    </div>
  );
}
