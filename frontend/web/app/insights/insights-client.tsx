"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { getMe } from "@/lib/auth-api";
import {
  Insight,
  InsightSeverity,
  InsightStatus,
  generateInsights,
  listInsights,
  sendInsightFeedback,
  updateInsightStatus,
} from "@/lib/insights-api";
import { Badge, Button, Card } from "@/components/ui";
import {
  AlertTriangle,
  CheckCircle,
  Eye,
  FileText,
  type LucideIcon,
} from "lucide-react";

const FILTERS: Array<{ label: string; status?: InsightStatus; severity?: InsightSeverity }> = [
  { label: "Đang hoạt động", status: "active" },
  { label: "Cảnh báo", status: "active", severity: "warning" },
  { label: "Rủi ro cao", status: "active", severity: "danger" },
  { label: "Đã ẩn", status: "dismissed" },
];

function toneForSeverity(severity: InsightSeverity): "blue" | "green" | "red" | "purple" | "neutral" {
  if (severity === "danger" || severity === "warning") return "red";
  if (severity === "success") return "green";
  if (severity === "watch") return "purple";
  return "blue";
}

function formatDmy(iso: string): string {
  const [y, m, d] = iso.split("-");
  return y && m && d ? `${d}/${m}/${y}` : iso;
}

function formatRange(insight: Insight): string {
  return `${formatDmy(insight.range_start)} → ${formatDmy(insight.range_end)}`;
}

const SEVERITY_LABELS: Record<string, string> = {
  danger: "Rủi ro",
  warning: "Cảnh báo",
  watch: "Cần chú ý",
  success: "Tốt",
  info: "Thông tin",
};

function severityLabel(severity: string): string {
  return SEVERITY_LABELS[severity] ?? "Thông tin";
}

// Chỉ hiển thị các trường evidence có ý nghĩa với người dùng (bỏ trường kỹ thuật).
// Mỗi entry: nhãn tiếng Việt + cách format giá trị.
const EVIDENCE_FIELDS: Record<string, { label: string; kind: "money" | "percent" | "count" | "text" }> = {
  total_amount: { label: "Số tiền", kind: "money" },
  current_amount: { label: "Kỳ này", kind: "money" },
  previous_amount: { label: "Kỳ trước", kind: "money" },
  current_total: { label: "Tổng kỳ này", kind: "money" },
  previous_total: { label: "Tổng kỳ trước", kind: "money" },
  delta_amount: { label: "Chênh lệch", kind: "money" },
  budget_amount: { label: "Ngân sách", kind: "money" },
  spent_amount: { label: "Đã chi", kind: "money" },
  spent_so_far: { label: "Đã chi", kind: "money" },
  projected_spend: { label: "Dự kiến", kind: "money" },
  weekday_avg: { label: "TB ngày thường", kind: "money" },
  weekend_avg: { label: "TB cuối tuần", kind: "money" },
  percentage: { label: "Tỷ trọng", kind: "percent" },
  percent_used: { label: "Đã dùng", kind: "percent" },
  projected_percent: { label: "Dự kiến dùng", kind: "percent" },
  delta_percent: { label: "Thay đổi", kind: "percent" },
  transaction_count: { label: "Số giao dịch", kind: "count" },
  new_merchant_count: { label: "Cửa hàng mới", kind: "count" },
  category_name: { label: "Danh mục", kind: "text" },
  merchant_name: { label: "Cửa hàng", kind: "text" },
  projected_exceed_date: { label: "Dự kiến chạm hạn mức", kind: "text" },
};

function formatVndFromRaw(raw: unknown): string {
  const num = Number(raw);
  if (!Number.isFinite(num)) return String(raw);
  return `${Math.round(num).toLocaleString("vi-VN", { maximumFractionDigits: 0 })} VND`;
}

function formatEvidenceValue(kind: string, value: unknown): string {
  switch (kind) {
    case "money":
      return formatVndFromRaw(value);
    case "percent": {
      const n = Number(value);
      return Number.isFinite(n) ? `${n.toFixed(1)}%` : String(value);
    }
    case "count": {
      const n = Number(value);
      return Number.isFinite(n) ? `${n} giao dịch` : String(value);
    }
    default:
      return String(value);
  }
}

/** Rút các trường evidence có ý nghĩa thành list {label, value} đã format. */
function readableEvidence(evidence: Record<string, unknown>[]): Array<{ label: string; value: string }> {
  const out: Array<{ label: string; value: string }> = [];
  const seen = new Set<string>();
  for (const row of evidence) {
    for (const [key, raw] of Object.entries(row)) {
      const field = EVIDENCE_FIELDS[key];
      if (!field || seen.has(key) || raw === null || raw === undefined || raw === "") continue;
      seen.add(key);
      out.push({ label: field.label, value: formatEvidenceValue(field.kind, raw) });
    }
  }
  return out;
}

type InsightAction = { type?: string; label?: string; params?: Record<string, unknown> };

function actionHref(action: InsightAction): string | null {
  const params = action.params ?? {};
  const categoryId = params.category_id;
  const query = typeof categoryId === "number" ? `?category_id=${categoryId}` : "";
  switch (action.type) {
    case "open_transactions":
      return `/transactions${query}`;
    case "open_budgets":
      return "/budgets";
    case "open_analytics":
      return "/analytics";
    default:
      return null;
  }
}

export default function InsightsClient() {
  const router = useRouter();
  const [authReady, setAuthReady] = useState(false);
  const [filterIndex, setFilterIndex] = useState(0);
  const [items, setItems] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

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

  const activeFilter = useMemo(() => FILTERS[filterIndex], [filterIndex]);
  const stats = useMemo(() => ({
    active: items.filter((item) => item.status === "active").length,
    danger: items.filter((item) => item.severity === "danger").length,
    warning: items.filter((item) => item.severity === "warning").length,
    evidence: items.filter((item) => item.evidence.length > 0).length,
  }), [items]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listInsights({
        status: activeFilter.status,
        severity: activeFilter.severity,
        limit: 30,
      });
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tải insights");
    } finally {
      setLoading(false);
    }
  }, [activeFilter]);

  useEffect(() => {
    if (authReady) void load();
  }, [authReady, load]);

  const onGenerate = async () => {
    setGenerating(true);
    setError(null);
    setNotice(null);
    try {
      const response = await generateInsights({ range: "30d", force_refresh: true });
      setItems(response.items);
      setNotice(`Đã tạo ${response.generated_count} insight mới từ dữ liệu giao dịch.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tạo insight");
    } finally {
      setGenerating(false);
    }
  };

  const onDismiss = async (insight: Insight) => {
    try {
      const updated = await updateInsightStatus(insight.id, "dismissed");
      setItems((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      setNotice("Insight đã được ẩn khỏi feed hoạt động.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể cập nhật insight");
    }
  };

  const onFeedback = async (insight: Insight, rating: "helpful" | "not_helpful") => {
    try {
      await sendInsightFeedback(insight.id, rating);
      setNotice(rating === "helpful" ? "Đã ghi nhận insight hữu ích." : "Đã ghi nhận phản hồi để cải thiện.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể gửi phản hồi");
    }
  };

  if (!authReady) {
    return <p className="text-body-sm text-mute">Đang kiểm tra phiên đăng nhập...</p>;
  }

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <h1 className="text-xl font-bold tracking-tight text-ink">Thông tin Insights</h1>
            <p className="mt-0.5 text-sm text-ash">
              Gợi ý phương pháp cắt giảm chi tiêu không thiết yếu dựa trên dữ liệu thật.
            </p>
          </div>
          <Button onClick={onGenerate} disabled={generating}>
            {generating ? "Đang tạo..." : "Tạo insight mới"}
          </Button>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <InsightStat icon={CheckCircle} label="Đang hiển thị" value={String(stats.active)} detail="Insight còn hiệu lực" tone="green" />
          <InsightStat icon={AlertTriangle} label="Rủi ro cao" value={String(stats.danger)} detail="Cần xử lý sớm" tone="red" />
          <InsightStat icon={Eye} label="Theo dõi" value={String(stats.warning)} detail="Đang cần chú ý" tone="purple" />
          <InsightStat icon={FileText} label="Có dữ liệu" value={String(stats.evidence)} detail="Có bằng chứng đối chiếu" tone="blue" />
        </div>
      </header>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((filter, index) => (
          <button
            key={filter.label}
            type="button"
            onClick={() => setFilterIndex(index)}
            className={`rounded-md border px-3 py-2 text-button-sm ${
              filterIndex === index
                ? "border-ink bg-ink text-on-dark"
                : "border-hairline bg-surface-card text-body hover:text-ink"
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {notice && <div className="rounded-md border border-accent-green bg-accent-green-soft p-3 text-body-sm text-accent-green">{notice}</div>}
      {error && <div className="rounded-md border border-accent-red bg-accent-red-soft p-3 text-body-sm text-accent-red">{error}</div>}
      {loading && <Card>Đang tải insight...</Card>}

      {!loading && (
        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((insight) => (
            <Card key={insight.id} className="space-y-4 border-hairline-soft bg-surface-card">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Badge tone={toneForSeverity(insight.severity)}>{severityLabel(insight.severity)}</Badge>
                <span className="text-caption-sm text-mute">{formatRange(insight)}</span>
              </div>
              <div>
                <h2 className="text-heading-sm-mixed text-ink">{insight.title}</h2>
                <p className="mt-2 text-body-sm text-body">{insight.summary}</p>
              </div>
              {readableEvidence(insight.evidence).length > 0 && (
                <div className="rounded-md border border-hairline-soft bg-surface-doc p-3">
                  <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Số liệu</p>
                  <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1.5">
                    {readableEvidence(insight.evidence).map((item) => (
                      <div key={item.label} className="flex justify-between gap-2 text-caption-sm">
                        <dt className="text-mute">{item.label}</dt>
                        <dd className="font-medium text-ink">{item.value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}
              {insight.actions.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {(insight.actions as InsightAction[]).map((action, idx) => {
                    const href = actionHref(action);
                    if (!href || !action.label) return null;
                    return (
                      <Button
                        key={`${action.type}-${idx}`}
                        variant="secondary"
                        size="sm"
                        onClick={() => router.push(href)}
                      >
                        {action.label}
                      </Button>
                    );
                  })}
                </div>
              )}
              <div className="flex flex-wrap justify-between gap-2 border-t border-hairline-soft pt-3">
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={() => void onFeedback(insight, "helpful")}>Hữu ích</Button>
                  <Button variant="tertiary" size="sm" onClick={() => void onFeedback(insight, "not_helpful")}>Chưa đúng</Button>
                </div>
                {insight.status === "active" && (
                  <Button variant="tertiary" size="sm" onClick={() => void onDismiss(insight)}>Ẩn</Button>
                )}
              </div>
            </Card>
          ))}
          {items.length === 0 && (
            <Card className="lg:col-span-2">
              <p className="text-body-sm text-mute">Chưa có insight phù hợp bộ lọc hiện tại.</p>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function InsightStat({ icon: Icon, label, value, detail, tone }: { icon: LucideIcon; label: string; value: string; detail: string; tone: "green" | "red" | "purple" | "blue" }) {
  const toneClass = {
    green: "bg-accent-green-soft text-accent-green",
    red: "bg-accent-red-soft text-accent-red",
    purple: "bg-accent-purple-soft text-accent-purple",
    blue: "bg-accent-blue-soft text-link-blue",
  }[tone];
  return (
    <article className="rounded-xl border border-hairline-soft bg-surface-doc p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">{label}</p>
          <p className="mt-2 text-2xl font-black text-ink">{value}</p>
        </div>
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${toneClass}`}>
          <Icon className="h-4.5 w-4.5" aria-hidden />
        </span>
      </div>
      <p className="mt-2 text-caption-sm text-mute">{detail}</p>
    </article>
  );
}
