import { Suspense } from "react";

import { TransactionHistoryClient } from "./transaction-history-client";

function TransactionsLoading() {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-8">
      <p className="text-sm text-slate-600">Đang tải trang giao dịch...</p>
    </section>
  );
}

export default function TransactionHistoryPage() {
  return (
    <Suspense fallback={<TransactionsLoading />}>
      <TransactionHistoryClient />
    </Suspense>
  );
}
