"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { getMe } from "@/lib/auth-api";
import {
  InvoiceData,
  Transaction,
  TransactionListFilters,
  TransactionListMeta,
  deleteTransaction,
  getTransactionInvoice,
  listTransactions,
} from "@/lib/transactions-api";
import {
  Badge,
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

function InvoiceDetailView({
  transactionId,
  hasInvoice,
}: {
  transactionId: number;
  hasInvoice: boolean;
}) {
  const [invoice, setInvoice] = useState<InvoiceData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!hasInvoice) {
      setIsLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getTransactionInvoice(transactionId);
        if (!cancelled) setInvoice(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Không tải được hóa đơn.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [transactionId, hasInvoice]);

  if (isLoading) {
    return (
      <div className="px-4 py-6 text-body-sm text-mute">
        Đang tải chi tiết hóa đơn...
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-4">
        <CalloutBanner severity="warning">{error}</CalloutBanner>
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="px-4 py-4 text-body-sm text-mute">
        Giao dịch này không có hóa đơn điện tử đính kèm.
      </div>
    );
  }

  return (
    <div className="px-4 py-4 space-y-4 bg-surface-soft/30">
      <h3 className="text-body-md font-semibold text-ink">Chi tiết hóa đơn điện tử</h3>

      {/* Invoice Metadata */}
      <div className="grid gap-2 md:grid-cols-2 text-body-sm">
        <div><span className="text-mute">Số hóa đơn:</span> {invoice.invoice_number ?? <span className="text-mute italic">—</span>}</div>
        <div><span className="text-mute">Mẫu số/Ký hiệu:</span> {invoice.template_symbol ?? <span className="text-mute italic">—</span>}</div>
        <div><span className="text-mute">Ngày lập:</span> {invoice.issue_date ?? <span className="text-mute italic">—</span>}</div>
        <div><span className="text-mute">Mã tra cứu:</span> {invoice.tax_lookup_code ?? <span className="text-mute italic">—</span>}</div>
        <div><span className="text-mute">Loại tiền tệ:</span> {invoice.currency}</div>
      </div>

      {/* Seller */}
      <div className="border-t border-hairline pt-3">
        <h4 className="text-body-xs font-semibold text-mute uppercase mb-2">Người bán</h4>
        <div className="grid gap-1 text-body-sm">
          <div><span className="text-mute">Tên:</span> {invoice.seller_name ?? <span className="text-mute italic">—</span>}</div>
          <div><span className="text-mute">MST:</span> {invoice.seller_tax_id ?? <span className="text-mute italic">—</span>}</div>
          <div><span className="text-mute">Địa chỉ:</span> {invoice.seller_address ?? <span className="text-mute italic">—</span>}</div>
        </div>
      </div>

      {/* Buyer */}
      <div className="border-t border-hairline pt-3">
        <h4 className="text-body-xs font-semibold text-mute uppercase mb-2">Người mua</h4>
        <div className="grid gap-1 text-body-sm">
          <div><span className="text-mute">Tên:</span> {invoice.buyer_name ?? <span className="text-mute italic">—</span>}</div>
          <div><span className="text-mute">MST:</span> {invoice.buyer_tax_id ?? <span className="text-mute italic">—</span>}</div>
          <div><span className="text-mute">Địa chỉ:</span> {invoice.buyer_address ?? <span className="text-mute italic">—</span>}</div>
          <div><span className="text-mute">Hình thức TT:</span> {invoice.payment_method ?? <span className="text-mute italic">—</span>}</div>
        </div>
      </div>

      {/* Line Items Table */}
      {invoice.line_items.length > 0 ? (
        <div className="border-t border-hairline pt-3">
          <h4 className="text-body-xs font-semibold text-mute uppercase mb-2">Chi tiết hàng hóa / dịch vụ</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-body-sm">
              <thead>
                <tr className="border-b border-hairline text-left text-mute">
                  <th className="py-2 pr-2">#</th>
                  <th className="py-2 pr-2">Tên hàng hóa</th>
                  <th className="py-2 pr-2">ĐVT</th>
                  <th className="py-2 pr-2 text-right">SL</th>
                  <th className="py-2 pr-2 text-right">Đơn giá</th>
                  <th className="py-2 pr-2 text-right">Thành tiền</th>
                  <th className="py-2 pr-2 text-right">VAT %</th>
                  <th className="py-2 text-right">Tiền thuế</th>
                </tr>
              </thead>
              <tbody>
                {invoice.line_items.map((item) => (
                  <tr key={item.id} className="border-b border-hairline/50">
                    <td className="py-2 pr-2 text-mute">{item.line_number + 1}</td>
                    <td className="py-2 pr-2">{item.item_name}</td>
                    <td className="py-2 pr-2">{item.unit ?? "—"}</td>
                    <td className="py-2 pr-2 text-right">{item.quantity}</td>
                    <td className="py-2 pr-2 text-right">{Number(item.unit_price).toLocaleString("vi-VN")}</td>
                    <td className="py-2 pr-2 text-right">{Number(item.line_total).toLocaleString("vi-VN")}</td>
                    <td className="py-2 pr-2 text-right">{item.vat_rate ? `${item.vat_rate}%` : "—"}</td>
                    <td className="py-2 text-right">{item.vat_amount ? Number(item.vat_amount).toLocaleString("vi-VN") : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {/* Totals */}
      <div className="border-t border-hairline pt-3">
        <h4 className="text-body-xs font-semibold text-mute uppercase mb-2">Tổng cộng</h4>
        <div className="grid gap-1 text-body-sm">
          <div className="flex justify-between"><span className="text-mute">Tổng trước thuế:</span> <span>{invoice.subtotal_before_tax ? Number(invoice.subtotal_before_tax).toLocaleString("vi-VN") + " " + invoice.currency : "—"}</span></div>
          <div className="flex justify-between"><span className="text-mute">Tổng tiền thuế:</span> <span>{invoice.total_tax ? Number(invoice.total_tax).toLocaleString("vi-VN") + " " + invoice.currency : "—"}</span></div>
          <div className="flex justify-between font-semibold"><span>Tổng thanh toán:</span> <span>{invoice.grand_total ? Number(invoice.grand_total).toLocaleString("vi-VN") + " " + invoice.currency : "—"}</span></div>
          {invoice.amount_in_words ? <div className="text-mute italic text-caption-sm">{invoice.amount_in_words}</div> : null}
        </div>
      </div>

      {/* Authentication */}
      {(invoice.digital_signature || invoice.signing_date || invoice.lookup_link) ? (
        <div className="border-t border-hairline pt-3">
          <h4 className="text-body-xs font-semibold text-mute uppercase mb-2">Xác thực</h4>
          <div className="grid gap-1 text-body-sm">
            {invoice.signing_date ? <div><span className="text-mute">Ngày ký:</span> {invoice.signing_date}</div> : null}
            {invoice.digital_signature ? <div><span className="text-mute">Chữ ký số:</span> <span className="text-accent-green">✓ Có</span></div> : null}
            {invoice.lookup_link ? <div><span className="text-mute">Tra cứu:</span> <a href={invoice.lookup_link} target="_blank" rel="noopener noreferrer" className="text-link-teal hover:underline">{invoice.lookup_link}</a></div> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
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
  const [expandedId, setExpandedId] = useState<number | null>(null);
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
      setExpandedId(null);
      await fetchList(appliedFilters, page);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Xóa giao dịch thất bại.",
      );
    } finally {
      setDeletingId(null);
    }
  };

  const onRowClick = (id: number) => {
    setExpandedId((prev) => (prev === id ? null : id));
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
                  <th className="px-4 py-3">Danh mục</th>
                  <th className="px-4 py-3 text-right">Số tiền</th>
                  <th className="px-4 py-3">Ghi chú</th>
                  <th className="px-4 py-3 text-right">Hành động</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline-soft">
                {items.map((transaction) => (
                  <TransactionRow
                    key={transaction.id}
                    transaction={transaction}
                    isExpanded={expandedId === transaction.id}
                    isDeleting={deletingId === transaction.id}
                    onRowClick={onRowClick}
                    onDelete={onDelete}
                  />
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

function TransactionRow({
  transaction,
  isExpanded,
  isDeleting,
  onRowClick,
  onDelete,
}: {
  transaction: Transaction;
  isExpanded: boolean;
  isDeleting: boolean;
  onRowClick: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <>
      <tr
        className={`cursor-pointer hover:bg-surface-soft/50 ${isExpanded ? "bg-surface-soft/30" : ""}`}
        onClick={() => onRowClick(transaction.id)}
      >
        <td className="px-4 py-3 font-mono text-caption-sm text-body">
          {transaction.transaction_date}
        </td>
        <td className="px-4 py-3 text-ink">
          <div className="flex items-center gap-2">
            {transaction.merchant_name ?? (
              <span className="text-ash">Không có</span>
            )}
            {transaction.has_invoice ? (
              <Badge tone="green" aria-label="Có hóa đơn">HĐ</Badge>
            ) : null}
          </div>
        </td>
        <td className="px-4 py-3 text-body">
          {transaction.category_name ?? (
            <span className="text-ash">Chưa phân loại</span>
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
            onClick={(e) => {
              e.stopPropagation();
              onDelete(transaction.id);
            }}
            disabled={isDeleting}
          >
            {isDeleting ? "Đang xóa..." : "Xóa"}
          </Button>
        </td>
      </tr>
      {isExpanded ? (
        <tr>
          <td colSpan={6} className="p-0 border-t border-hairline">
            <InvoiceDetailView
              transactionId={transaction.id}
              hasInvoice={transaction.has_invoice}
            />
          </td>
        </tr>
      ) : null}
    </>
  );
}
