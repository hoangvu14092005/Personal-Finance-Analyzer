"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getMe } from "@/lib/auth-api";
import {
  DEFAULT_RANGE_PRESET,
  RANGE_LABELS,
  RANGE_PRESETS,
  type RangePreset,
} from "@/lib/dashboard-api";
import {
  ALERT_SEVERITY_LABELS,
  generateInsight,
  getLatestInsight,
  isInsightEmpty,
  type AlertItem,
  type AlertSeverity,
  type InsightItem,
  type InsightResponse,
  type RecommendationItem,
} from "@/lib/insights-api";

const VISIBLE_RANGES: RangePreset[] = ["7d", "30d", "this_month", "last_month"];

function severityClass(severity: AlertSeverity): string {
  switch (severity) {
    case "critical":
      return "border-rose-300 bg-rose-50 text-rose-900";
    case "warning":
      return "border-amber-300 bg-amber-50 text-amber-900";
    case "info":
    default:
      return "border-sky-300 bg-sky-50 text-sky-900";
  }
}

function severityBadgeClass(severity: AlertSeverity): string {
  switch (severity) {
    case "critical":
      return "bg-rose-200 text-rose-900";
    case "warning":
      return "bg-amber-200 text-amber-900";
    case "info":
    default:
      return "bg-sky-200 text-sky-900";
  }
}

function formatGeneratedAt(iso: string): string {
  // "2026-05-05T12:30:00+00:00" -> "2026-05-05 19:30 (ICT)" approximately;
  // dùng toLocaleString user locale để cover client TZ.
  try {
    const d = new Date(iso);
    return d.toLocaleString("vi-VN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function formatVnd(value: string | null): string | null {
  if (value === null) return null;
  const num = Number(value);
  if (!Number.isFinite(num)) return value;
  return num.toLocaleString("vi-VN", { maximumFractionDigits: 0 });
}

export default function InsightsClient() {
  const router = useRouter();

  const [authReady, setAuthReady] = useState(false);
  const [range, setRange] = useState<RangePreset>(DEFAULT_RANGE_PRESET);

  const [insight, setInsight] = useState<InsightResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  // Auth gate.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await getMe();
        if (!cancelled) setAuthReady(true);
      } catch {
        router.replace("/login?next=/insights");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  const fetchLatest = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const result = await getLatestInsight(range);
      setInsight(result);
    } catch (err) {
      const e = err as Error & { status?: number };
      if (e.status === 404) {
        setInsight(null);
        setNotFound(true);
      } else {
        setError(e.message || "Không tải được insight.");
      }
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    if (!authReady) return;
    void fetchLatest();
  }, [authReady, fetchLatest]);

  const onGenerate = useCallback(
    async (force: boolean) => {
      setGenerating(true);
      setError(null);
      setNotFound(false);
      try {
        const result = await generateInsight({ range, force });
        setInsight(result);
      } catch (err) {
        const e = err as Error;
        setError(e.message || "Không sinh được insight.");
      } finally {
        setGenerating(false);
      }
    },
    [range],
  );

  if (!authReady) {
    return (
      <div className="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-500">
        Đang kiểm tra phiên đăng nhập…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            AI Insights
          </h1>
          <p className="text-sm text-slate-500">
            Phân tích thói quen chi tiêu và đề xuất ngắn gọn dựa trên dữ liệu
            gần đây.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div
            role="tablist"
            aria-label="Phạm vi thời gian"
            className="inline-flex rounded-full border border-slate-200 bg-white p-1 text-sm"
          >
            {VISIBLE_RANGES.map((preset) => (
              <button
                key={preset}
                type="button"
                role="tab"
                aria-selected={range === preset}
                onClick={() => setRange(preset)}
                className={`rounded-full px-3 py-1 transition ${
                  range === preset
                    ? "bg-slate-900 text-white shadow"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {RANGE_LABELS[preset]}
              </button>
            ))}
          </div>

          <button
            type="button"
            disabled={generating}
            onClick={() => void onGenerate(false)}
            className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60"
          >
            {generating ? "Đang sinh insight…" : "Sinh insight"}
          </button>
          <button
            type="button"
            disabled={generating}
            onClick={() => void onGenerate(true)}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-60"
            title="Bỏ qua cache, gọi lại provider"
          >
            Làm mới
          </button>
        </div>
      </header>

      {RANGE_PRESETS.includes(range) && range === "custom" ? (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          Phạm vi tùy chỉnh hiện chưa được hỗ trợ ở trang này — hãy chọn 1 trong
          các preset trên.
        </div>
      ) : null}

      {error ? (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-4 text-sm text-rose-900">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Đang tải insight…
        </div>
      ) : null}

      {!loading && notFound ? (
        <div className="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-600">
          Chưa có insight cho phạm vi{" "}
          <span className="font-medium">{RANGE_LABELS[range]}</span>. Bấm{" "}
          <span className="font-medium">Sinh insight</span> để tạo mới.
        </div>
      ) : null}

      {!loading && insight ? <InsightView insight={insight} /> : null}
    </div>
  );
}

function InsightView({ insight }: { insight: InsightResponse }) {
  const { status, status_reason, payload, range, provider, generated_at, cached } = insight;

  if (status === "insufficient_data") {
    return (
      <section className="rounded-md border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900">
          Chưa đủ dữ liệu để sinh insight
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          {status_reason ??
            "Hãy thêm thêm vài giao dịch trải đều theo ngày rồi thử lại."}
        </p>
        <p className="mt-2 text-xs text-slate-400">
          Phạm vi: {range.start} → {range.end}
        </p>
      </section>
    );
  }

  if (status === "failed") {
    return (
      <section className="rounded-md border border-rose-200 bg-rose-50 p-6">
        <h2 className="text-lg font-semibold text-rose-900">
          Tạo insight thất bại
        </h2>
        <p className="mt-2 text-sm text-rose-800">
          {status_reason ?? "Provider không phản hồi. Vui lòng thử lại sau."}
        </p>
      </section>
    );
  }

  if (isInsightEmpty(payload)) {
    return (
      <section className="rounded-md border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900">
          Không có cảnh báo nào
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Chi tiêu trong kỳ ổn định, không có pattern bất thường.
        </p>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <MetaBar
        provider={provider}
        generatedAt={generated_at}
        cached={cached}
        rangeStart={range.start}
        rangeEnd={range.end}
      />

      {payload.alerts.length > 0 ? (
        <section className="space-y-3">
          <h2 className="text-base font-semibold text-slate-900">Cảnh báo</h2>
          <div className="space-y-3">
            {payload.alerts.map((alert, idx) => (
              <AlertCard key={idx} alert={alert} />
            ))}
          </div>
        </section>
      ) : null}

      {payload.insights.length > 0 ? (
        <section className="space-y-3">
          <h2 className="text-base font-semibold text-slate-900">Phân tích</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {payload.insights.map((item, idx) => (
              <InsightCard key={idx} item={item} />
            ))}
          </div>
        </section>
      ) : null}

      {payload.recommendations.length > 0 ? (
        <section className="space-y-3">
          <h2 className="text-base font-semibold text-slate-900">Đề xuất</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {payload.recommendations.map((item, idx) => (
              <RecommendationCard key={idx} item={item} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function MetaBar({
  provider,
  generatedAt,
  cached,
  rangeStart,
  rangeEnd,
}: {
  provider: string;
  generatedAt: string;
  cached: boolean;
  rangeStart: string;
  rangeEnd: string;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-600">
      <span>
        Phạm vi: <span className="font-medium text-slate-800">{rangeStart}</span> →{" "}
        <span className="font-medium text-slate-800">{rangeEnd}</span>
      </span>
      <span className="flex items-center gap-2">
        <span>
          Provider: <span className="font-medium text-slate-800">{provider}</span>
        </span>
        <span>•</span>
        <span>Tạo lúc {formatGeneratedAt(generatedAt)}</span>
        {cached ? (
          <span className="ml-1 inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-800">
            Cache
          </span>
        ) : null}
      </span>
    </div>
  );
}

function AlertCard({ alert }: { alert: AlertItem }) {
  return (
    <article
      className={`rounded-md border p-4 text-sm ${severityClass(alert.severity)}`}
    >
      <header className="flex items-center justify-between gap-3">
        <h3 className="text-base font-semibold">{alert.title}</h3>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${severityBadgeClass(alert.severity)}`}
        >
          {ALERT_SEVERITY_LABELS[alert.severity]}
        </span>
      </header>
      <p className="mt-2 leading-relaxed">{alert.body}</p>
    </article>
  );
}

function InsightCard({ item }: { item: InsightItem }) {
  return (
    <article className="rounded-md border border-slate-200 bg-white p-4 text-sm">
      <h3 className="text-base font-semibold text-slate-900">{item.title}</h3>
      <p className="mt-2 text-slate-600 leading-relaxed">{item.body}</p>
    </article>
  );
}

function RecommendationCard({ item }: { item: RecommendationItem }) {
  const savings = formatVnd(item.estimated_savings);
  return (
    <article className="rounded-md border border-emerald-200 bg-emerald-50/40 p-4 text-sm">
      <h3 className="text-base font-semibold text-emerald-900">{item.title}</h3>
      <p className="mt-2 text-emerald-900/90 leading-relaxed">{item.body}</p>
      {savings ? (
        <p className="mt-2 text-xs font-medium text-emerald-800">
          Tiết kiệm ước tính: {savings} VND
        </p>
      ) : null}
    </article>
  );
}
