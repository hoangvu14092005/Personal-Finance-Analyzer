"use client";

import { useEffect, useMemo, useState } from "react";

import { apiBaseUrl } from "@/lib/config";

type HealthState = {
  status: "idle" | "loading" | "online" | "offline";
  message: string;
  latencyMs?: number;
};

export default function HealthPage() {
  const [healthState, setHealthState] = useState<HealthState>({
    status: "idle",
    message: "Chua thuc hien kiem tra API.",
  });

  const endpoint = useMemo(() => `${apiBaseUrl}/health`, []);

  useEffect(() => {
    let isCancelled = false;

    const probe = async () => {
      setHealthState({ status: "loading", message: "Dang kiem tra ket noi API..." });
      const startedAt = performance.now();

      try {
        const response = await fetch(endpoint, {
          cache: "no-store",
          headers: {
            "X-Request-ID": "frontend-health-page",
          },
        });

        const elapsed = Math.round(performance.now() - startedAt);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const body = (await response.json()) as { service?: string; status?: string };
        if (isCancelled) {
          return;
        }

        setHealthState({
          status: "online",
          message: `API ${body.service ?? "unknown"} tra ve status=${body.status ?? "unknown"}.`,
          latencyMs: elapsed,
        });
      } catch (error) {
        if (isCancelled) {
          return;
        }

        const message = error instanceof Error ? error.message : "Unknown error";
        setHealthState({
          status: "offline",
          message: `Khong the ket noi API: ${message}`,
        });
      }
    };

    void probe();

    return () => {
      isCancelled = true;
    };
  }, [endpoint]);

  const cardClasses =
    healthState.status === "online"
      ? "border-emerald-200 bg-emerald-50"
      : healthState.status === "offline"
        ? "border-rose-200 bg-rose-50"
        : "border-slate-200 bg-slate-50";

  const title =
    healthState.status === "online"
      ? "Status: ONLINE"
      : healthState.status === "offline"
        ? "Status: OFFLINE"
        : "Status: CHECKING";

  return (
    <section className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">
        Frontend Health Check
      </h1>

      <div className={`rounded-xl border p-5 ${cardClasses}`}>
        <p className="text-sm font-semibold text-slate-900">{title}</p>
        <p className="mt-2 text-sm text-slate-700">{healthState.message}</p>
        <p className="mt-2 text-xs text-slate-600">Endpoint: {endpoint}</p>
        {healthState.latencyMs !== undefined ? (
          <p className="mt-1 text-xs text-slate-600">
            Latency: {healthState.latencyMs}ms
          </p>
        ) : null}
      </div>
    </section>
  );
}
