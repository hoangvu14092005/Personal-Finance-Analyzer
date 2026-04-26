"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { CategoryBreakdown } from "@/lib/dashboard-api";

// Fallback colors khi category không có color (system) — đồng bộ với donut ring.
const FALLBACK_COLORS = [
  "#0ea5e9",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#a855f7",
  "#64748b",
];

export type CategoryChartProps = {
  categories: CategoryBreakdown[];
  totalSpend: string;
};

type ChartDatum = {
  name: string;
  value: number;
  color: string;
  percentage: number;
};

function formatVnd(numeric: number): string {
  return numeric.toLocaleString("vi-VN", { maximumFractionDigits: 0 });
}

export function CategoryChart({ categories, totalSpend }: CategoryChartProps) {
  // Map sang shape recharts dùng (numeric value). Bỏ entries 0 để pie không
  // render slice ma.
  const chartData: ChartDatum[] = categories
    .map((cat, index) => ({
      name: cat.name,
      value: Number(cat.total_amount),
      color: cat.color ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length],
      percentage: cat.percentage,
    }))
    .filter((d) => Number.isFinite(d.value) && d.value > 0);

  if (chartData.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-500">
        Không có dữ liệu để vẽ biểu đồ
      </div>
    );
  }

  const totalNumeric = Number(totalSpend);

  return (
    <div className="grid grid-cols-1 items-center gap-4 md:grid-cols-2">
      {/* Donut chart */}
      <div className="relative h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={2}
              stroke="#fff"
            >
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name) => {
                const numeric = typeof value === "number" ? value : Number(value);
                const safeNumeric = Number.isFinite(numeric) ? numeric : 0;
                return [`${formatVnd(safeNumeric)} VND`, String(name)];
              }}
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #e2e8f0",
                fontSize: 12,
              }}
            />
          </PieChart>
        </ResponsiveContainer>

        {/* Tổng ở giữa donut */}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs uppercase tracking-wide text-slate-500">
            Tổng
          </span>
          <span className="text-lg font-bold text-slate-900">
            {Number.isFinite(totalNumeric) ? formatVnd(totalNumeric) : totalSpend}
          </span>
          <span className="text-xs text-slate-500">VND</span>
        </div>
      </div>

      {/* Legend */}
      <ul className="space-y-2 text-sm">
        {chartData.map((entry) => (
          <li key={entry.name} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-full"
                style={{ backgroundColor: entry.color }}
                aria-hidden="true"
              />
              <span className="text-slate-800">{entry.name}</span>
            </span>
            <span className="font-medium text-slate-900">
              {entry.percentage.toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
