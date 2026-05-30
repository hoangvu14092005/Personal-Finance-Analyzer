"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import type { FormEvent, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  ChevronRight,
  PiggyBank,
  ReceiptText,
  Sparkles,
  TrendingDown,
  TrendingUp,
  UploadCloud,
  Wallet,
  type LucideIcon,
} from "lucide-react";

import { getMe } from "@/lib/auth-api";
import type { BudgetUsage } from "@/lib/budgets-api";
import {
  DashboardSummary,
  DEFAULT_RANGE_PRESET,
  RangePreset,
  RANGE_LABELS,
  RANGE_PRESETS,
  getDashboardSummary,
  isRangePreset,
} from "@/lib/dashboard-api";

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

function formatMoney(value: string | number, currency = "VND"): string {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return `${value} ${currency}`;
  return `${numeric.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} ${currency}`;
}

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return y && m && d ? `${d}/${m}/${y}` : iso;
}

function formatDelta(deltaAmount: string, deltaPercent: number | null) {
  const numeric = Number(deltaAmount);
  if (!Number.isFinite(numeric) || numeric === 0) {
    return { label: "Không đổi", color: "text-mute", tone: "neutral" as const };
  }
  const isIncrease = numeric > 0;
  const sign = isIncrease ? "+" : "-";
  const pct = deltaPercent === null ? "" : ` (${sign}${Math.abs(deltaPercent).toFixed(1)}%)`;
  return {
    label: `${sign}${formatMoney(Math.abs(numeric))}${pct}`,
    color: isIncrease ? "text-accent-red" : "text-accent-green",
    tone: isIncrease ? ("risk" as const) : ("good" as const),
  };
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
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>(() =>
    readFiltersFromSearch(new URLSearchParams(searchParams.toString())),
  );
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const { user } = await getMe();
        if (!cancelled) {
          setDisplayName(user.full_name?.trim() || user.email);
          setAuthReady(true);
        }
      } catch {
        router.replace("/login?next=/dashboard");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    setFilters(readFiltersFromSearch(new URLSearchParams(searchParams.toString())));
  }, [searchParams]);

  const apiParams = useMemo(() => {
    if (filters.preset !== "custom") return { range: filters.preset };
    if (filters.startDate && filters.endDate) {
      return {
        range: "custom" as const,
        start_date: filters.startDate,
        end_date: filters.endDate,
      };
    }
    const end = todayIso();
    const start = shiftIso(end, -29);
    return { range: "custom" as const, start_date: start, end_date: end };
  }, [filters]);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await getDashboardSummary(apiParams);
      setData(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tải dashboard");
    } finally {
      setLoading(false);
    }
  }, [apiParams]);

  useEffect(() => {
    if (authReady) void refetch();
  }, [authReady, refetch]);

  const selectPreset = (preset: RangePreset) => {
    const next = new URLSearchParams();
    next.set("range", preset);
    router.replace(`/dashboard?${next.toString()}`);
  };

  const submitCustom = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!filters.startDate || !filters.endDate) {
      setError("Vui lòng chọn đủ ngày bắt đầu và kết thúc.");
      return;
    }
    if (filters.startDate > filters.endDate) {
      setError("Ngày bắt đầu phải trước ngày kết thúc.");
      return;
    }
    const next = new URLSearchParams();
    next.set("range", "custom");
    next.set("start_date", filters.startDate);
    next.set("end_date", filters.endDate);
    router.replace(`/dashboard?${next.toString()}`);
  };

  if (!authReady) {
    return <ShellLoading label="Đang kiểm tra phiên đăng nhập..." />;
  }

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <h1 className="text-xl font-bold tracking-tight text-ink">
              Chào mừng trở lại{displayName ? `, ${displayName}` : ""}!
            </h1>
            <p className="mt-0.5 text-sm text-ash">
              Xem báo cáo tổng thể, ngân sách và phân tích tài chính ngày hôm nay.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/receipts/upload"
              className="rounded-lg bg-accent-green px-4 py-2.5 text-sm font-medium text-on-dark shadow-sm hover:bg-primary-pressed"
            >
              Tải hóa đơn lên
            </Link>
            <Link
              href="/transactions/new"
              className="rounded-lg border border-hairline bg-white px-4 py-2.5 text-sm font-medium text-ink hover:bg-surface-soft"
            >
              Ghi chép giao dịch
            </Link>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          {RANGE_PRESETS.filter((preset) => preset !== "custom").map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => selectPreset(preset)}
              className={`rounded-lg border px-3 py-2 text-button-sm transition-colors ${
                filters.preset === preset
                  ? "border-ink bg-ink text-on-dark"
                  : "border-hairline-soft bg-surface-doc text-body hover:text-ink"
              }`}
            >
              {RANGE_LABELS[preset]}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setFilters((prev) => ({ ...prev, preset: "custom" }))}
            className={`rounded-lg border px-3 py-2 text-button-sm transition-colors ${
              filters.preset === "custom"
                ? "border-ink bg-ink text-on-dark"
                : "border-hairline-soft bg-surface-doc text-body hover:text-ink"
            }`}
          >
            Tùy chỉnh
          </button>
        </div>

        {filters.preset === "custom" && (
          <form onSubmit={submitCustom} className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
            <DateInput
              label="Từ ngày"
              value={filters.startDate}
              onChange={(value) => setFilters((prev) => ({ ...prev, startDate: value }))}
            />
            <DateInput
              label="Đến ngày"
              value={filters.endDate}
              onChange={(value) => setFilters((prev) => ({ ...prev, endDate: value }))}
            />
            <button
              type="submit"
              className="self-end rounded-lg bg-ink px-4 py-2 text-button-sm font-bold text-on-dark"
            >
              Áp dụng
            </button>
          </form>
        )}
      </header>

      {error && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-accent-red/20 bg-accent-red-soft p-4 text-body-sm text-accent-red">
          <span>{error}</span>
          <button type="button" onClick={() => void refetch()} className="font-bold underline">
            Thử lại
          </button>
        </div>
      )}

      {loading && !data && <DashboardSkeleton />}
      {!loading && data && data.current.transaction_count === 0 && <EmptyState />}
      {data && data.current.transaction_count > 0 && <DashboardContent data={data} refreshing={loading} />}
    </div>
  );
}

function DateInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="space-y-1">
      <span className="text-caption-xs text-mute">{label}</span>
      <input
        type="date"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-lg border border-hairline-soft bg-surface-card px-3 text-body-sm text-ink"
      />
    </label>
  );
}

function ShellLoading({ label }: { label: string }) {
  return (
    <section className="rounded-2xl border border-hairline-soft bg-surface-card p-8">
      <p className="text-body-sm text-mute">{label}</p>
    </section>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((item) => (
          <div key={item} className="h-32 animate-pulse rounded-2xl border border-hairline-soft bg-surface-soft" />
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-12">
        <div className="h-80 animate-pulse rounded-2xl border border-hairline-soft bg-surface-soft xl:col-span-8" />
        <div className="h-80 animate-pulse rounded-2xl border border-hairline-soft bg-surface-soft xl:col-span-4" />
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <section className="rounded-xl border border-dashed border-hairline bg-white p-10 text-center">
      <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Chưa có giao dịch</p>
      <h2 className="mt-2 text-heading-lg text-ink">Chưa có dữ liệu để phân tích</h2>
      <p className="mx-auto mt-2 max-w-xl text-body-sm text-body">
        Ghi chép giao dịch thủ công hoặc tải hóa đơn lên để AI bóc tách rồi lưu vào sổ ví.
      </p>
      <div className="mt-5 flex flex-wrap justify-center gap-3">
        <Link href="/receipts/upload" className="rounded-lg bg-accent-green px-4 py-2 text-button-sm font-bold text-on-dark">
          Tải hóa đơn lên
        </Link>
        <Link href="/transactions/new" className="rounded-lg border border-hairline bg-surface-card px-4 py-2 text-button-sm font-bold text-ink">
          Ghi chép giao dịch
        </Link>
      </div>
    </section>
  );
}

function DashboardContent({ data, refreshing }: { data: DashboardSummary; refreshing: boolean }) {
  const delta = formatDelta(data.delta_amount, data.delta_percent);
  const budgetRisk = useMemo(() => {
    const exceeded = data.budgets_usage.filter((item) => item.status === "exceeded").length;
    const warning = data.budgets_usage.filter((item) => item.status === "warning").length;
    return { exceeded, warning };
  }, [data.budgets_usage]);
  const topCategory = data.top_categories[0];
  const highestBudget = data.budgets_usage[0];

  return (
    <section className={`space-y-5 ${refreshing ? "opacity-70" : ""}`}>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Tổng chi tiêu"
          value={formatMoney(data.current.total_spend)}
          detail={`${data.current.transaction_count} giao dịch · ${data.range.days} ngày`}
          tone="red"
          icon={ArrowDownRight}
        />
        <StatCard
          label="Biến động kỳ này"
          value={<span className={delta.color}>{delta.label}</span>}
          detail={`So với ${formatDate(data.previous_range.start)} - ${formatDate(data.previous_range.end)}`}
          tone={delta.tone === "risk" ? "red" : delta.tone === "good" ? "green" : "neutral"}
          icon={delta.tone === "good" ? TrendingDown : TrendingUp}
        />
        <StatCard
          label="Cảnh báo ngân sách"
          value={`${budgetRisk.exceeded + budgetRisk.warning}`}
          detail={`${budgetRisk.exceeded} vượt · ${budgetRisk.warning} sắp vượt`}
          tone={budgetRisk.exceeded > 0 ? "red" : budgetRisk.warning > 0 ? "amber" : "green"}
          icon={PiggyBank}
        />
        <StatCard
          label="Danh mục nổi bật"
          value={topCategory?.name ?? "Chưa có"}
          detail={topCategory ? `${formatMoney(topCategory.total_amount)} · ${topCategory.percentage.toFixed(1)}%` : "Chờ thêm dữ liệu"}
          tone="blue"
          icon={Wallet}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-12">
        <Panel className="xl:col-span-8" title="Chi tiêu theo danh mục" eyebrow="Phân tích dòng tiền" action={<Link href="/analytics" className="text-button-sm text-accent-green hover:underline">Phân tích chi tiết</Link>}>
          <CategoryBars categories={data.top_categories} total={Number(data.current.total_spend) || 1} />
        </Panel>

        <Panel className="xl:col-span-4" title="Cơ cấu ngân sách" eyebrow="Ngưỡng kiểm soát">
          <div className="space-y-4">
            {highestBudget ? (
              <BudgetRiskCard usage={highestBudget} />
            ) : (
              <div className="rounded-xl border border-dashed border-hairline-soft p-4 text-body-sm text-mute">
                Chưa có budget. Tạo budget để bật cảnh báo sớm.
              </div>
            )}
            <div className="rounded-xl border border-hairline-soft bg-surface-doc p-4">
              <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Ghi chú dữ liệu</p>
              <p className="mt-2 text-body-sm text-body">
                Hóa đơn OCR cần được xác nhận thành giao dịch trước khi cộng vào báo cáo và ngân sách.
              </p>
            </div>
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-12">
        <Panel className="xl:col-span-7" title="Giao dịch phát sinh gần đây" eyebrow="Nhật ký giao dịch" action={<Link href="/transactions" className="text-button-sm text-accent-green hover:underline">Nhật ký giao dịch</Link>}>
          <RecentTransactions data={data} />
        </Panel>
        <Panel className="xl:col-span-5" title="Thao tác nhanh" eyebrow="Lối tắt">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <ActionCard href="/receipts/upload" title="Tải hóa đơn lên (OCR)" body="AI bóc tách hóa đơn, bạn kiểm tra rồi ghi vào sổ ví." />
            <ActionCard href="/insights" title="Thông tin Insights" body="Nhận gợi ý tối ưu chi tiêu dựa trên giao dịch thực tế." />
            <ActionCard href="/chat" title="Trợ lý tài chính (AI)" body="Đặt câu hỏi về chi tiêu, ngân sách hoặc hóa đơn bằng tiếng Việt." />
          </div>
        </Panel>
      </div>
    </section>
  );
}

function StatCard({ label, value, detail, tone, icon: Icon }: { label: string; value: ReactNode; detail: string; tone: "red" | "green" | "amber" | "blue" | "neutral"; icon: LucideIcon }) {
  const toneClass = {
    red: "bg-accent-red-soft text-accent-red",
    green: "bg-accent-green-soft text-accent-green",
    amber: "bg-primary/20 text-primary-active",
    blue: "bg-accent-blue-soft text-link-blue",
    neutral: "bg-surface-soft text-body",
  }[tone];

  return (
    <article className="rounded-xl border border-hairline-soft bg-white p-5 transition-all hover:shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">{label}</p>
          <p className="mt-3 text-2xl font-black text-ink">{value}</p>
        </div>
        <span className={`flex h-11 w-11 items-center justify-center rounded-lg ${toneClass}`} aria-hidden>
          <Icon className="h-5.5 w-5.5 stroke-[2.2]" />
        </span>
      </div>
      <p className="mt-3 text-caption-sm text-mute">{detail}</p>
    </article>
  );
}

function Panel({ title, eyebrow, action, className = "", children }: { title: string; eyebrow: string; action?: ReactNode; className?: string; children: ReactNode }) {
  return (
    <section className={`rounded-xl border border-hairline-soft bg-white p-5 ${className}`}>
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">{eyebrow}</p>
          <h2 className="mt-1 text-heading-sm-mixed text-ink">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function CategoryBars({ categories, total }: { categories: DashboardSummary["top_categories"]; total: number }) {
  if (categories.length === 0) {
    return <p className="text-body-sm text-mute">Chưa có danh mục để hiển thị.</p>;
  }
  return (
    <div className="space-y-4">
      {categories.slice(0, 7).map((category, index) => {
        const amount = Number(category.total_amount) || 0;
        const width = Math.max(4, (amount / total) * 100);
        return (
          <div key={`${category.category_id ?? "category"}-${category.name}`} className="grid gap-2 md:grid-cols-[150px_1fr_120px] md:items-center">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-surface-soft text-caption-xs font-black text-mute">
                {index + 1}
              </span>
              <span className="truncate text-body-sm font-semibold text-ink">{category.name}</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-surface-soft">
              <div
                className="h-full rounded-full bg-accent-green"
                style={{ width: `${Math.min(100, width)}%` }}
              />
            </div>
            <div className="text-right text-caption-sm text-mute">
              <span className="font-bold text-ink">{formatMoney(category.total_amount)}</span>
              <span className="block">{category.percentage.toFixed(1)}%</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function BudgetRiskCard({ usage }: { usage: BudgetUsage }) {
  const statusLabel = usage.status === "exceeded" ? "Vượt ngân sách" : usage.status === "warning" ? "Sắp vượt" : "An toàn";
  const statusClass = usage.status === "exceeded" ? "text-accent-red" : usage.status === "warning" ? "text-primary-active" : "text-accent-green";
  return (
    <div className="rounded-lg border border-hairline-soft p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
        <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Danh mục cần chú ý</p>
          <p className="mt-1 text-body-strong text-ink">{usage.category_name}</p>
        </div>
        <span className={`text-caption-md font-bold ${statusClass}`}>{statusLabel}</span>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-surface-soft">
        <div
          className={usage.status === "exceeded" ? "h-full bg-accent-red" : usage.status === "warning" ? "h-full bg-primary" : "h-full bg-accent-green"}
          style={{ width: `${Math.min(100, usage.percent_used)}%` }}
        />
      </div>
      <p className="mt-3 text-caption-sm text-mute">
        {formatMoney(usage.spent_amount)} / {formatMoney(usage.budget_amount)} · {usage.percent_used.toFixed(0)}%
      </p>
    </div>
  );
}

function RecentTransactions({ data }: { data: DashboardSummary }) {
  return (
    <div className="divide-y divide-hairline-soft">
      {data.recent_transactions.map((tx) => (
        <Link key={tx.id} href={`/transactions/${tx.id}`} className="grid gap-2 py-3 hover:bg-surface-doc sm:grid-cols-[1fr_auto] sm:items-center">
          <div>
            <p className="text-body-sm font-bold text-ink">{tx.merchant_name ?? "Không có merchant"}</p>
            <p className="text-caption-sm text-mute">
              {formatDate(tx.transaction_date)}{tx.category_name ? ` · ${tx.category_name}` : ""}
            </p>
          </div>
          <div className="text-left text-body-sm font-black text-ink sm:text-right">
            {formatMoney(tx.amount, tx.currency)}
          </div>
        </Link>
      ))}
    </div>
  );
}

function ActionCard({ href, title, body }: { href: string; title: string; body: string }) {
  const Icon = href.includes("receipts") ? UploadCloud : href.includes("chat") ? ArrowUpRight : href.includes("insights") ? Sparkles : ReceiptText;
  return (
    <Link href={href} className="flex gap-3 rounded-lg border border-hairline-soft bg-surface-doc p-4 transition-colors hover:bg-surface-soft">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-green-soft text-accent-green">
        <Icon className="h-4.5 w-4.5" aria-hidden />
      </span>
      <span className="min-w-0">
        <span className="block text-body-strong text-ink">{title}</span>
        <span className="mt-1 block text-caption-sm text-mute">{body}</span>
      </span>
      <ChevronRight className="ml-auto mt-1 h-4 w-4 shrink-0 text-stone" aria-hidden />
    </Link>
  );
}
