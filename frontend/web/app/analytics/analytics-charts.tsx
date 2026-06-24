"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { categoryColor, FALLBACK_PALETTE, formatVnd, formatVndShort } from "@/lib/chart-colors";

const TOOLTIP_STYLE = {
  borderRadius: 8,
  border: "1px solid var(--color-hairline)",
  background: "var(--color-surface-card)",
  fontSize: 12,
} as const;

function shortDate(iso: string): string {
  const [, m, d] = iso.split("-");
  return m && d ? `${d}/${m}` : iso;
}

// --- Trend (area) ---

export type TrendDatum = { period_start: string; amount: string; transaction_count: number };

export function TrendAreaChart({ points }: { points: TrendDatum[] }) {
  const data = points.map((p) => ({
    label: shortDate(p.period_start),
    amount: Number(p.amount) || 0,
    count: p.transaction_count,
  }));
  return (
    <div className="h-56 w-full" role="img" aria-label="Biểu đồ xu hướng chi tiêu theo thời gian">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
          <defs>
            <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2c84e0" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#2c84e0" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#64748b" }}
            tickLine={false}
            axisLine={{ stroke: "#e2e8f0" }}
            interval="preserveStartEnd"
            minTickGap={20}
          />
          <YAxis
            tickFormatter={(v) => formatVndShort(Number(v))}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value) => [formatVnd(Number(value)), "Chi tiêu"]}
            labelFormatter={(label) => `Ngày ${label}`}
          />
          <Area
            type="monotone"
            dataKey="amount"
            stroke="#2c84e0"
            strokeWidth={2}
            fill="url(#trendFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// --- Category donut ---

export type DonutDatum = { name: string; value: number; color: string; percentage: number };

export function CategoryDonut({ data, total }: { data: DonutDatum[]; total: number }) {
  const slices = data.filter((d) => Number.isFinite(d.value) && d.value > 0);
  if (slices.length === 0) {
    return <p className="flex h-56 items-center justify-center text-body-sm text-mute">Chưa có dữ liệu.</p>;
  }
  return (
    <div className="relative h-56 w-full" role="img" aria-label="Biểu đồ phân bổ chi phí theo danh mục">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={slices}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={62}
            outerRadius={92}
            paddingAngle={2}
            stroke="#fff"
          >
            {slices.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, name) => [formatVnd(Number(value)), String(name)]}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-caption-xs uppercase tracking-wide text-mute">Tổng</span>
        <span className="text-body-strong text-ink">{formatVnd(total)}</span>
      </div>
    </div>
  );
}

// --- Horizontal bar (merchant / product) ---

export type HBarDatum = { name: string; value: number; color?: string };

export function HorizontalBarChart({ data, maxItems = 8 }: { data: HBarDatum[]; maxItems?: number }) {
  const rows = data.slice(0, maxItems).map((d, i) => ({
    name: d.name,
    value: Number(d.value) || 0,
    color: d.color ?? FALLBACK_PALETTE[i % FALLBACK_PALETTE.length],
  }));
  if (rows.length === 0) {
    return <p className="text-body-sm text-mute">Chưa có dữ liệu.</p>;
  }
  const height = Math.max(120, rows.length * 36);
  return (
    <div style={{ height }} className="w-full" role="img" aria-label="Biểu đồ so sánh theo cột ngang">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
          <XAxis type="number" hide tickFormatter={(v) => formatVndShort(Number(v))} />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 12, fill: "#475569" }}
            tickLine={false}
            axisLine={false}
            width={130}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            cursor={{ fill: "rgba(148,163,184,0.08)" }}
            formatter={(value) => [formatVnd(Number(value)), "Tổng chi"]}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={22}>
            {rows.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export { categoryColor };
