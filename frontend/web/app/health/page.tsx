"use client";

import { useEffect, useMemo, useState } from "react";

import { apiBaseUrl } from "@/lib/config";
import { CalloutBanner, Card, DisplayLg } from "@/components/ui";

type HealthState = {
  status: "idle" | "loading" | "online" | "offline";
  message: string;
  latencyMs?: number;
};

export default function HealthPage() {
  const [healthState, setHealthState] = useState<HealthState>({
    status: "idle",
    message: "Chưa thực hiện kiểm tra API.",
  });

  const endpoint = useMemo(() => `${apiBaseUrl}/health`, []);

  useEffect(() => {
    let isCancelled = false;

    const probe = async () => {
      setHealthState({ status: "loading", message: "Đang kiểm tra kết nối API..." });
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
          message: `API ${body.service ?? "unknown"} trả về status=${body.status ?? "unknown"}.`,
          latencyMs: elapsed,
        });
      } catch (error) {
        if (isCancelled) {
          return;
        }

        const message = error instanceof Error ? error.message : "Unknown error";
        setHealthState({
          status: "offline",
          message: `Không thể kết nối API: ${message}`,
        });
      }
    };

    void probe();

    return () => {
      isCancelled = true;
    };
  }, [endpoint]);

  const severity: "info" | "success" | "warning" =
    healthState.status === "online"
      ? "success"
      : healthState.status === "offline"
        ? "warning"
        : "info";

  const title =
    healthState.status === "online"
      ? "Status: ONLINE"
      : healthState.status === "offline"
        ? "Status: OFFLINE"
        : "Status: CHECKING";

  return (
    <div className="space-y-6">
      <DisplayLg>Frontend Health Check</DisplayLg>

      <CalloutBanner severity={severity} title={title}>
        {healthState.message}
      </CalloutBanner>

      <Card variant="doc">
        <dl className="space-y-2 text-body-sm">
          <div className="flex gap-2">
            <dt className="text-mute min-w-24">Endpoint:</dt>
            <dd className="text-ink font-mono">{endpoint}</dd>
          </div>
          {healthState.latencyMs !== undefined ? (
            <div className="flex gap-2">
              <dt className="text-mute min-w-24">Latency:</dt>
              <dd className="text-ink">{healthState.latencyMs}ms</dd>
            </div>
          ) : null}
        </dl>
      </Card>
    </div>
  );
}
