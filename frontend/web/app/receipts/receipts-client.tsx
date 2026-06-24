"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Eye,
  FileText,
  Filter,
  ReceiptText,
  Search,
  UploadCloud,
  type LucideIcon,
} from "lucide-react";

import { getMe } from "@/lib/auth-api";
import {
  ReceiptListFilters,
  ReceiptListItem,
  ReceiptListMeta,
  listReceipts,
  receiptFileUrl,
} from "@/lib/receipts-api";
import {
  Badge,
  Button,
  CalloutBanner,
  Card,
  DisplayLg,
  Input,
} from "@/components/ui";

const DEFAULT_PAGE_SIZE = 20;

type SelectValue = "" | "true" | "false";

type FilterFormState = {
  receiptDate: string;
  createdDate: string;
  merchant: string;
  status: string;
  ocrStatus: string;
  hasTransaction: SelectValue;
  hasInvoice: SelectValue;
};

const EMPTY_FILTERS: FilterFormState = {
  receiptDate: "",
  createdDate: "",
  merchant: "",
  status: "",
  ocrStatus: "",
  hasTransaction: "",
  hasInvoice: "",
};

function optionalBool(value: SelectValue): boolean | undefined {
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}

function toApiFilters(form: FilterFormState, page: number): ReceiptListFilters {
  return {
    receipt_date: form.receiptDate || undefined,
    created_date: form.createdDate || undefined,
    merchant: form.merchant.trim() || undefined,
    status: form.status || undefined,
    ocr_status: form.ocrStatus || undefined,
    has_transaction: optionalBool(form.hasTransaction),
    has_invoice: optionalBool(form.hasInvoice),
    page,
    size: DEFAULT_PAGE_SIZE,
  };
}

function formatAmount(amount: string | null, currency: string | null): string {
  if (!amount) return "-";
  const numeric = Number(amount);
  if (!Number.isFinite(numeric)) return `${amount} ${currency ?? ""}`.trim();
  return `${numeric.toLocaleString("vi-VN", { maximumFractionDigits: 2 })} ${
    currency ?? ""
  }`.trim();
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusTone(status: string): "blue" | "green" | "red" | "neutral" {
  const normalized = status.toLowerCase();
  if (["ready", "succeeded", "confirmed"].includes(normalized)) return "green";
  if (["failed", "error"].includes(normalized)) return "red";
  if (["processing", "running", "pending", "uploaded"].includes(normalized)) {
    return "blue";
  }
  return "neutral";
}

export function ReceiptsClient() {
  const router = useRouter();
  const [authReady, setAuthReady] = useState(false);
  const [filters, setFilters] = useState<FilterFormState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterFormState>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<ReceiptListItem[] | null>(null);
  const [meta, setMeta] = useState<ReceiptListMeta | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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

  const fetchList = useCallback(async (form: FilterFormState, targetPage: number) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await listReceipts(toApiFilters(form, targetPage));
      setItems(response.items);
      setMeta(response.meta);
    } catch (error) {
      setItems([]);
      setMeta(null);
      setErrorMessage(
        error instanceof Error ? error.message : "Không tải được danh sách hóa đơn.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authReady) return;
    void fetchList(appliedFilters, page);
  }, [authReady, appliedFilters, page, fetchList]);

  const onApplyFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPage(1);
    setAppliedFilters(filters);
  };

  const onResetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setPage(1);
  };

  const totalPages = useMemo(() => {
    if (!meta || meta.size <= 0) return 1;
    return Math.max(1, Math.ceil(meta.total / meta.size));
  }, [meta]);

  const stats = useMemo(() => {
    const current = items ?? [];
    return {
      visible: current.length,
      linked: current.filter((item) => item.linked_transaction).length,
      invoice: current.filter((item) => item.has_invoice).length,
      needsReview: current.filter((item) => !item.linked_transaction).length,
    };
  }, [items]);

  if (!authReady) {
    return (
      <Card>
        <p className="text-body-sm text-mute">Đang xác thực phiên đăng nhập...</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <DisplayLg>Nhật ký danh sách hóa đơn tải lên</DisplayLg>
            <p className="mt-0.5 text-sm text-ash">
              Tìm lại hóa đơn đã tải, xem trạng thái OCR và đối chiếu giao dịch đã ghi sổ.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/receipts/upload">
              <Button variant="primary" size="sm"><UploadCloud className="h-4 w-4" aria-hidden />Tải hóa đơn lên</Button>
            </Link>
            <Link href="/transactions">
              <Button variant="secondary" size="sm"><ReceiptText className="h-4 w-4" aria-hidden />Sổ giao dịch</Button>
            </Link>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <ReceiptStat icon={ReceiptText} label="Đang hiển thị" value={String(stats.visible)} detail={`${meta?.total ?? 0} hóa đơn trong hệ thống`} tone="neutral" />
          <ReceiptStat icon={CheckCircle} label="Đã ghi sổ" value={String(stats.linked)} detail="Đã liên kết giao dịch" tone="green" />
          <ReceiptStat icon={AlertTriangle} label="Cần kiểm tra" value={String(stats.needsReview)} detail="OCR chưa được xác nhận" tone="amber" />
          <ReceiptStat icon={FileText} label="Hóa đơn VAT" value={String(stats.invoice)} detail="Có dữ liệu pháp lý/VAT" tone="blue" />
        </div>
      </header>

      <Card className="border-hairline-soft bg-surface-card">
        <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-caption-xs font-bold uppercase tracking-wide text-mute">
              <Filter className="h-3.5 w-3.5" aria-hidden />
              Bộ lọc hóa đơn
            </p>
            <h2 className="text-heading-sm-mixed text-ink">Tìm chứng từ đã tải lên</h2>
          </div>
          <p className="text-caption-sm text-mute">Có thể lọc theo ngày hóa đơn, ngày upload hoặc cửa hàng.</p>
        </div>
        <form onSubmit={onApplyFilters} className="grid gap-4 md:grid-cols-4">
          <label className="text-body-xs text-ink">
            Ngày hóa đơn
            <Input
              type="date"
              value={filters.receiptDate}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, receiptDate: event.target.value }))
              }
              className="mt-1.5"
            />
          </label>
          <label className="text-body-xs text-ink">
            Ngày upload
            <Input
              type="date"
              value={filters.createdDate}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, createdDate: event.target.value }))
              }
              className="mt-1.5"
            />
          </label>
          <label className="text-body-xs text-ink md:col-span-2">
            Cửa hàng
            <span className="relative mt-1.5 block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ash" aria-hidden />
              <Input
                type="text"
                placeholder="VD: Highlands, Grab, Coop..."
                value={filters.merchant}
                onChange={(event) =>
                  setFilters((prev) => ({ ...prev, merchant: event.target.value }))
                }
                className="pl-9"
              />
            </span>
          </label>
          <label className="text-body-xs text-ink">
            Trạng thái hóa đơn
            <select
              value={filters.status}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, status: event.target.value }))
              }
              className="mt-1.5 h-9 w-full rounded-md border border-hairline bg-surface-card px-3 text-body-md text-ink focus:border-accent-blue focus:outline-none focus:ring-2 focus:ring-accent-blue/20"
            >
              <option value="">Tất cả</option>
              <option value="uploaded">Đã tải lên</option>
              <option value="processing">Đang xử lý</option>
              <option value="ready">Sẵn sàng</option>
              <option value="failed">Lỗi</option>
            </select>
          </label>
          <label className="text-body-xs text-ink">
            Trạng thái OCR
            <select
              value={filters.ocrStatus}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, ocrStatus: event.target.value }))
              }
              className="mt-1.5 h-9 w-full rounded-md border border-hairline bg-surface-card px-3 text-body-md text-ink focus:border-accent-blue focus:outline-none focus:ring-2 focus:ring-accent-blue/20"
            >
              <option value="">Tất cả</option>
              <option value="pending">Đang chờ</option>
              <option value="running">Đang chạy</option>
              <option value="succeeded">Thành công</option>
              <option value="failed">Lỗi</option>
            </select>
          </label>
          <label className="text-body-xs text-ink">
            Giao dịch
            <select
              value={filters.hasTransaction}
              onChange={(event) =>
                setFilters((prev) => ({
                  ...prev,
                  hasTransaction: event.target.value as SelectValue,
                }))
              }
              className="mt-1.5 h-9 w-full rounded-md border border-hairline bg-surface-card px-3 text-body-md text-ink focus:border-accent-blue focus:outline-none focus:ring-2 focus:ring-accent-blue/20"
            >
              <option value="">Tất cả</option>
              <option value="true">Đã tạo</option>
              <option value="false">Chưa tạo</option>
            </select>
          </label>
          <label className="text-body-xs text-ink">
            Hóa đơn VAT
            <select
              value={filters.hasInvoice}
              onChange={(event) =>
                setFilters((prev) => ({
                  ...prev,
                  hasInvoice: event.target.value as SelectValue,
                }))
              }
              className="mt-1.5 h-9 w-full rounded-md border border-hairline bg-surface-card px-3 text-body-md text-ink focus:border-accent-blue focus:outline-none focus:ring-2 focus:ring-accent-blue/20"
            >
              <option value="">Tất cả</option>
              <option value="true">Có hóa đơn VAT</option>
              <option value="false">Receipt thường</option>
            </select>
          </label>
          <div className="flex items-center gap-2 md:col-span-4">
            <Button type="submit" variant="primary" size="sm">Áp dụng</Button>
            <Button type="button" variant="secondary" size="sm" onClick={onResetFilters}>
              Đặt lại
            </Button>
          </div>
        </form>
      </Card>

      {errorMessage ? <CalloutBanner severity="warning">{errorMessage}</CalloutBanner> : null}

      <Card className="overflow-hidden p-0 border-hairline-soft">
        {isLoading ? (
          <p className="p-6 text-body-sm text-mute">Đang tải hóa đơn...</p>
        ) : items && items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-body-sm">
              <thead className="border-b border-hairline bg-surface-soft text-utility-xs text-body">
                <tr>
                  <th className="px-4 py-3">Chứng từ</th>
                  <th className="px-4 py-3">Cửa hàng</th>
                  <th className="px-4 py-3">Ngày hóa đơn</th>
                  <th className="px-4 py-3">Ngày upload</th>
                  <th className="px-4 py-3 text-right">Tổng OCR</th>
                  <th className="px-4 py-3">Trạng thái</th>
                  <th className="px-4 py-3 text-right">Hành động</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline-soft">
                {items.map((receipt) => (
                  <ReceiptRow key={receipt.receipt_id} receipt={receipt} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="space-y-2 p-8 text-center">
            <p className="text-body-strong text-ink">Không có hóa đơn nào khớp bộ lọc.</p>
            <p className="text-caption-sm text-mute">
              Upload hóa đơn mới hoặc đặt lại bộ lọc để xem toàn bộ chứng từ.
            </p>
          </div>
        )}
      </Card>

      {meta && meta.total > 0 ? (
        <div className="flex items-center justify-between text-body-sm text-body">
          <p>
            Trang <span className="font-semibold text-ink">{meta.page}</span> / {totalPages} ·
            Tổng <span className="font-semibold text-ink">{meta.total}</span> hóa đơn
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

function ReceiptRow({ receipt }: { receipt: ReceiptListItem }) {
  const transaction = receipt.linked_transaction;
  return (
    <tr className="hover:bg-surface-soft/50">
      <td className="px-4 py-3">
        <div className="flex min-w-64 items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-hairline-soft bg-surface-doc text-caption-xs font-black text-mute">
            <ReceiptText className="h-5 w-5" aria-hidden />
          </div>
          <div className="min-w-0 space-y-1">
            <Link
              href={`/receipts/${receipt.receipt_id}/review`}
              className="block truncate font-semibold text-link-teal hover:underline"
            >
              #{receipt.receipt_id} · {receipt.file_name}
            </Link>
            <p className="truncate text-caption-sm text-mute">{receipt.content_type}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3 text-ink">
        {receipt.merchant_name ?? <span className="text-ash">Chưa nhận diện</span>}
      </td>
      <td className="px-4 py-3 font-mono text-caption-sm text-body">
        {receipt.receipt_date ?? <span className="text-ash">-</span>}
      </td>
      <td className="px-4 py-3 text-caption-sm text-body">
        {formatDateTime(receipt.created_at)}
      </td>
      <td className="px-4 py-3 text-right font-semibold text-ink">
        {formatAmount(receipt.total_amount, receipt.currency)}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={statusTone(receipt.status)}>{receipt.status}</Badge>
          <Badge tone={statusTone(receipt.ocr_status)}>OCR {receipt.ocr_status}</Badge>
          {receipt.has_invoice ? <Badge tone="purple">VAT</Badge> : null}
          {transaction ? <Badge tone="green">TX #{transaction.transaction_id}</Badge> : <Badge tone="blue">Chờ ghi sổ</Badge>}
        </div>
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex flex-wrap justify-end gap-2">
          <a
            href={receiptFileUrl(receipt.receipt_id)}
            target="_blank"
            rel="noreferrer"
          >
            <Button type="button" variant="secondary" size="sm">
              <Eye className="h-4 w-4" aria-hidden />
              Xem hóa đơn
            </Button>
          </a>
          <Link href={`/receipts/${receipt.receipt_id}/review`}>
            <Button type="button" variant="secondary" size="sm">
              Kiểm tra
            </Button>
          </Link>
          {transaction ? (
            <Link href={`/transactions?created=${transaction.transaction_id}`}>
              <Button type="button" variant="secondary" size="sm">
                Giao dịch
              </Button>
            </Link>
          ) : null}
        </div>
      </td>
    </tr>
  );
}

function ReceiptStat({ icon: Icon, label, value, detail, tone }: { icon: LucideIcon; label: string; value: string; detail: string; tone: "neutral" | "green" | "amber" | "blue" }) {
  const toneClass = {
    neutral: "bg-surface-doc text-ink",
    green: "bg-accent-green-soft text-accent-green",
    amber: "bg-primary/20 text-primary-active",
    blue: "bg-accent-blue-soft text-link-blue",
  }[tone];
  return (
    <article className="rounded-xl border border-hairline-soft bg-surface-doc p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">{label}</p>
          <p className="mt-2 text-2xl font-black text-ink">{value}</p>
        </div>
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${toneClass}`}>
          <Icon className="h-4.5 w-4.5" aria-hidden />
        </span>
      </div>
      <p className="mt-2 text-caption-sm text-mute">{detail}</p>
    </article>
  );
}
