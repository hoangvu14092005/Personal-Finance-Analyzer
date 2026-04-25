"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { getMe } from "@/lib/auth-api";
import {
  Transaction,
  TransactionListFilters,
  TransactionListMeta,
  deleteTransaction,
  listTransactions,
} from "@/lib/transactions-api";

const DEFAULT_PAGE_SIZE = 20;

type FilterFormState = {
  startDate: string;
  endDate: string;
  merchant: string;
};

const EMPTY_FILTERS: FilterFormState = {
  startDate: "",
  endDate: "",
  merchant: "",
};

function toApiFilters(form: FilterFormState, page: number): TransactionListFilters {
  return {
    start_date: form.startDate || undefined,
    end_date: form.endDate || undefined,
    merchant: form.merchant.trim() || undefined,
    page,
    size: DEFAULT_PAGE_SIZE,
  };
}

function formatAmount(amount: string, currency: string): string {
  const numeric = Number(amount);
  if (!Number.isFinite(numeric)) {
    return `${amount} ${currency}`;
  }
  return `${numeric.toLocaleString("vi-VN", { maximumFractionDigits: 2 })} ${currency}`;
}

export default function TransactionHistoryPage() {
  const router = useRouter();

  const [authReady, setAuthReady] = useState(false);
  const [filters, setFilters] = useState<FilterFormState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterFormState>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);

  const [items, setItems] = useState<Transaction[] | null>(null);
  const [meta, setMeta] = useState<TransactionListMeta | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Auth gate: redirect về login nếu chưa đăng nhập.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await getMe();
        if (!cancelled) setAuthReady(true);
      } catch {
        if (!cancelled) router.replace("/login");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  const fetchList = useCallback(
    async (form: FilterFormState, targetPage: number) => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const response = await listTransactions(toApiFilters(form, targetPage));
        setItems(response.items);
        setMeta(response.meta);
      } catch (error) {
        setItems([]);
        setMeta(null);
        setErrorMessage(
          error instanceof Error ? error.message : "Không tải được danh sách giao dịch.",
        );
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!authReady) return;
    void fetchList(appliedFilters, page);
  }, [authReady, appliedFilters, page, fetchList]);

  const onApplyFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatusMessage(null);
    setPage(1);
    setAppliedFilters(filters);
  };

  const onResetFilters = () => {
    setStatusMessage(null);
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setPage(1);
  };

  const onDelete = async (id: number) => {
    const confirmed = window.confirm(
      `Xóa giao dịch #${id}? Hành động này không thể hoàn tác.`,
    );
    if (!confirmed) return;
    setDeletingId(id);
    setStatusMessage(null);
    try {
      await deleteTransaction(id);
      setStatusMessage(`Đã xóa giao dịch #${id}.`);
      await fetchList(appliedFilters, page);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Xóa giao dịch thất bại.",
      );
    } finally {
      setDeletingId(null);
    }
  };

  const totalPages = useMemo(() => {
    if (!meta || meta.size <= 0) return 1;
    return Math.max(1, Math.ceil(meta.total / meta.size));
  }, [meta]);

  if (!authReady) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-sm text-slate-600">Đang xác thực phiên đăng nhập...</p>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Lịch sử giao dịch</h1>
          <p className="text-sm text-slate-600">
            Xem, lọc và quản lý giao dịch đã lưu.
          </p>
        </div>
      </header>

      <form
        onSubmit={onApplyFilters}
        className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:grid-cols-4"
      >
        <label className="text-sm font-medium text-slate-700">
          Từ ngày
          <input
            type="date"
            value={filters.startDate}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, startDate: event.target.value }))
            }
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Đến ngày
          <input
            type="date"
            value={filters.endDate}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, endDate: event.target.value }))
            }
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-sm font-medium text-slate-700 md:col-span-2">
          Tìm theo merchant
          <input
            type="text"
            placeholder="VD: Highlands, Pho 24..."
            value={filters.merchant}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, merchant: event.target.value }))
            }
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <div className="flex items-center gap-2 md:col-span-4">
          <button
            type="submit"
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
          >
            Áp dụng
          </button>
          <button
            type="button"
            onClick={onResetFilters}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          >
            Đặt lại
          </button>
        </div>
      </form>

      {statusMessage ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {statusMessage}
        </div>
      ) : null}
      {errorMessage ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {errorMessage}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {isLoading ? (
          <p className="p-6 text-sm text-slate-600">Đang tải giao dịch...</p>
        ) : items && items.length > 0 ? (
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Ngày</th>
                <th className="px-4 py-3">Merchant</th>
                <th className="px-4 py-3 text-right">Số tiền</th>
                <th className="px-4 py-3">Ghi chú</th>
                <th className="px-4 py-3 text-right">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((transaction) => (
                <tr key={transaction.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs text-slate-700">
                    {transaction.transaction_date}
                  </td>
                  <td className="px-4 py-3 text-slate-900">
                    {transaction.merchant_name ?? (
                      <span className="text-slate-400">Không có</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-slate-900">
                    {formatAmount(transaction.amount, transaction.currency)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {transaction.note ?? <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => onDelete(transaction.id)}
                      disabled={deletingId === transaction.id}
                      className="rounded-md border border-rose-200 px-3 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {deletingId === transaction.id ? "Đang xóa..." : "Xóa"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="space-y-2 p-8 text-center">
            <p className="text-sm font-semibold text-slate-700">
              Chưa có giao dịch nào khớp với bộ lọc.
            </p>
            <p className="text-xs text-slate-500">
              Thử upload hóa đơn ở mục Upload hoặc đặt lại bộ lọc.
            </p>
          </div>
        )}
      </div>

      {meta && meta.total > 0 ? (
        <div className="flex items-center justify-between text-sm text-slate-600">
          <p>
            Trang <span className="font-semibold">{meta.page}</span> / {totalPages} ·
            Tổng <span className="font-semibold">{meta.total}</span> giao dịch
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={meta.page <= 1 || isLoading}
              className="rounded-md border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Trang trước
            </button>
            <button
              type="button"
              onClick={() => setPage((prev) => prev + 1)}
              disabled={meta.page >= totalPages || isLoading}
              className="rounded-md border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Trang sau
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
