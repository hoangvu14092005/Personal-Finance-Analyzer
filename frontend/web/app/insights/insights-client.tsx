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

function formatRange(insight: Insight): string {
  return `${insight.range_start} → ${insight.range_end}`;
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
                <Badge tone={toneForSeverity(insight.severity)}>{insight.severity}</Badge>
                <span className="text-caption-sm text-mute">{formatRange(insight)}</span>
              </div>
              <div>
                <h2 className="text-heading-sm-mixed text-ink">{insight.title}</h2>
                <p className="mt-2 text-body-sm text-body">{insight.summary}</p>
              </div>
              {insight.evidence.length > 0 && (
                <div className="rounded-md border border-hairline-soft bg-surface-doc p-3">
                  <p className="text-caption-xs text-mute">Bằng chứng</p>
                  <div className="mt-2 space-y-1 text-caption-sm text-body">
                    {insight.evidence.slice(0, 3).map((evidence, idx) => (
                      <p key={idx}>{Object.entries(evidence).map(([key, value]) => `${key}: ${String(value)}`).join(" · ")}</p>
                    ))}
                  </div>
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
