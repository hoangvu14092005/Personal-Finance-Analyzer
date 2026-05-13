"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { getMe } from "@/lib/auth-api";
import {
  Transaction,
  TransactionListFilters,
  TransactionListMeta,
  deleteTransaction,
  listTransactions,
} from "@/lib/transactions-api";
import {
  Button,
  CalloutBanner,
  Card,
  DisplayLg,
  Input,
} from "@/components/ui";

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

export function TransactionHistoryClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const createdId = searchParams.get("created");

  const [authReady, setAuthReady] = useState(false);
  const [filters, setFilters] = useState<FilterFormState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterFormState>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);

  const [items, setItems] = useState<Transaction[] | null>(null);
  const [meta, setMeta] = useState<TransactionListMeta | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(
    createdId ? `Đã lưu giao dịch #${createdId}.` : null,
  );

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
      <Card>
        <p className="text-body-sm text-mute">Đang xác thực phiên đăng nhập...</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <DisplayLg>Lịch sử giao dịch</DisplayLg>
          <p className="text-body-sm text-body mt-1">
            Xem, lọc và quản lý giao dịch đã lưu.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/transactions/new">
            <Button variant="primary" size="sm">Nhập tay</Button>
          </Link>
          <Link href="/receipts/upload">
            <Button variant="secondary" size="sm">Upload hóa đơn</Button>
          </Link>
        </div>
      </header>

      <Card>
        <form onSubmit={onApplyFilters} className="grid gap-4 md:grid-cols-4">
          <label className="text-body-xs text-ink">
            Từ ngày
            <Input
              type="date"
              value={filters.startDate}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, startDate: event.target.value }))
              }
              className="mt-1.5"
            />
          </label>
          <label className="text-body-xs text-ink">
            Đến ngày
            <Input
              type="date"
              value={filters.endDate}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, endDate: event.target.value }))
              }
              className="mt-1.5"
            />
          </label>
          <label className="text-body-xs text-ink md:col-span-2">
            Tìm theo merchant
            <Input
              type="text"
              placeholder="VD: Highland, Grab, Coop..."
              value={filters.merchant}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, merchant: event.target.value }))
              }
              className="mt-1.5"
            />
          </label>
          <div className="flex items-center gap-2 md:col-span-4">
            <Button type="submit" variant="primary" size="sm">
              Áp dụng
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onResetFilters}
            >
              Đặt lại
            </Button>
          </div>
        </form>
      </Card>

      {statusMessage ? (
        <CalloutBanner severity="success">{statusMessage}</CalloutBanner>
      ) : null}
      {errorMessage ? (
        <CalloutBanner severity="warning">{errorMessage}</CalloutBanner>
      ) : null}

      <Card className="p-0 overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-body-sm text-mute">Đang tải giao dịch...</p>
        ) : items && items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-body-sm">
              <thead className="border-b border-hairline bg-surface-soft text-utility-xs text-body">
                <tr>
                  <th className="px-4 py-3">Ngày</th>
                  <th className="px-4 py-3">Merchant</th>
                  <th className="px-4 py-3 text-right">Số tiền</th>
                  <th className="px-4 py-3">Ghi chú</th>
                  <th className="px-4 py-3 text-right">Hành động</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline-soft">
                {items.map((transaction) => (
                  <tr key={transaction.id} className="hover:bg-surface-soft/50">
                    <td className="px-4 py-3 font-mono text-caption-sm text-body">
                      {transaction.transaction_date}
                    </td>
                    <td className="px-4 py-3 text-ink">
                      {transaction.merchant_name ?? (
                        <span className="text-ash">Không có</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-ink">
                      {formatAmount(transaction.amount, transaction.currency)}
                    </td>
                    <td className="px-4 py-3 text-body">
                      {transaction.note ?? <span className="text-ash">—</span>}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        type="button"
                        variant="danger"
                        size="sm"
                        onClick={() => onDelete(transaction.id)}
                        disabled={deletingId === transaction.id}
                      >
                        {deletingId === transaction.id ? "Đang xóa..." : "Xóa"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="space-y-2 p-8 text-center">
            <p className="text-body-strong text-ink">
              Chưa có giao dịch nào khớp với bộ lọc.
            </p>
            <p className="text-caption-sm text-mute">
              Thử upload hóa đơn ở mục Upload hoặc đặt lại bộ lọc.
            </p>
          </div>
        )}
      </Card>

      {meta && meta.total > 0 ? (
        <div className="flex items-center justify-between text-body-sm text-body">
          <p>
            Trang <span className="font-semibold text-ink">{meta.page}</span> / {totalPages} ·
            Tổng <span className="font-semibold text-ink">{meta.total}</span> giao dịch
          </p>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={meta.page <= 1 || isLoading}
            >
              Trang trước
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setPage((prev) => prev + 1)}
              disabled={meta.page >= totalPages || isLoading}
            >
              Trang sau
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
