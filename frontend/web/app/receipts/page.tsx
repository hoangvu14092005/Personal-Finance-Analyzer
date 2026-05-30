import { Suspense } from "react";

import { ReceiptsClient } from "./receipts-client";

function ReceiptsLoading() {
  return (
    <section className="rounded-lg border border-hairline-soft bg-surface-card p-8">
      <p className="text-body-sm text-mute">Đang tải danh sách hóa đơn...</p>
    </section>
  );
}

export default function ReceiptsPage() {
  return (
    <Suspense fallback={<ReceiptsLoading />}>
      <ReceiptsClient />
    </Suspense>
  );
}
