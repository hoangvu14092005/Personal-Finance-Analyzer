import { Suspense } from "react";

import { DashboardClient } from "./dashboard-client";

function DashboardLoading() {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-8">
      <p className="text-sm text-slate-600">Đang tải dashboard...</p>
    </section>
  );
}

export default function DashboardPage() {
  // Bọc Suspense vì `DashboardClient` dùng `useSearchParams` cho time filter
  // — Next.js 15 yêu cầu khi prerender static.
  return (
    <Suspense fallback={<DashboardLoading />}>
      <DashboardClient />
    </Suspense>
  );
}
