"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, use, useEffect, useMemo, useState } from "react";

import { getMe } from "@/lib/auth-api";
import { Category, listCategories } from "@/lib/categories-api";
import { DraftReview, getReceiptDraft, getReceiptInvoice, InvoiceData } from "@/lib/receipts-api";
import { createTransaction } from "@/lib/transactions-api";
import {
  Button,
  CalloutBanner,
  Card,
  DisplayLg,
  Input,
  Textarea,
} from "@/components/ui";

type ReviewFormState = {
  merchantName: string;
  amount: string;
  currency: string;
  transactionDate: string;
  categoryId: string;
  note: string;
};

const EMPTY_FORM: ReviewFormState = {
  merchantName: "",
  amount: "",
  currency: "VND",
  transactionDate: "",
  categoryId: "",
  note: "",
};

const LOW_CONFIDENCE_THRESHOLD = 0.7;

function draftToForm(draft: DraftReview): ReviewFormState {
  return {
    merchantName: draft.merchant_name ?? "",
    amount: draft.amount ?? "",
    currency: draft.currency ?? "VND",
    transactionDate: draft.transaction_date ?? "",
    categoryId:
      draft.suggested_category_id !== null
        ? String(draft.suggested_category_id)
        : "",
    note: "",
  };
}

export default function ReceiptReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const receiptId = Number(id);
  const router = useRouter();

  const [authReady, setAuthReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftReview | null>(null);
  const [invoice, setInvoice] = useState<InvoiceData | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState<ReviewFormState>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

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

  useEffect(() => {
    if (!authReady) return;
    if (!Number.isFinite(receiptId) || receiptId <= 0) {
      setLoadError("Receipt id không hợp lệ.");
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    (async () => {
      setIsLoading(true);
      setLoadError(null);
      try {
        const [draftResponse, categoriesResponse] = await Promise.all([
          getReceiptDraft(receiptId),
          listCategories(),
        ]);
        if (cancelled) return;
        setDraft(draftResponse);
        setCategories(categoriesResponse.items);
        setForm(draftToForm(draftResponse));

        // Try to load full invoice data (may not exist for old receipts)
        try {
          const invoiceResponse = await getReceiptInvoice(receiptId);
          if (!cancelled) setInvoice(invoiceResponse);
        } catch {
          // Invoice not found is OK - old receipts won't have it
        }
      } catch (error) {
        if (cancelled) return;
        setLoadError(
          error instanceof Error ? error.message : "Không tải được draft.",
        );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authReady, receiptId]);

  const isLowConfidence = useMemo(
    () =>
      draft !== null &&
      draft.confidence !== null &&
      draft.confidence < LOW_CONFIDENCE_THRESHOLD,
    [draft],
  );

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    const trimmedAmount = form.amount.trim();
    if (!trimmedAmount) {
      setSubmitError("Số tiền là bắt buộc.");
      return;
    }
    if (!form.transactionDate) {
      setSubmitError("Ngày giao dịch là bắt buộc.");
      return;
    }

    setSubmitting(true);
    try {
      const created = await createTransaction({
        amount: trimmedAmount,
        currency: form.currency.trim().toUpperCase() || "VND",
        transaction_date: form.transactionDate,
        merchant_name: form.merchantName.trim() || null,
        category_id: form.categoryId ? Number(form.categoryId) : null,
        receipt_upload_id: receiptId,
        note: form.note.trim() || null,
      });
      router.push(`/transactions?created=${created.id}`);
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Lưu giao dịch thất bại.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (!authReady) {
    return (
      <Card>
        <p className="text-body-sm text-mute">Đang xác thực phiên đăng nhập...</p>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <p className="text-body-sm text-mute">Đang tải dữ liệu OCR draft...</p>
      </Card>
    );
  }

  if (loadError) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <CalloutBanner severity="warning" title="Không tải được draft">
          {loadError}
        </CalloutBanner>
        <p className="text-body-sm text-body">
          Bạn có thể chờ OCR hoàn thành rồi tải lại, hoặc{" "}
          <Link
            href="/transactions/new"
            className="text-link-teal font-semibold hover:underline"
          >
            nhập tay
          </Link>
          .
        </p>
      </div>
    );
  }

  const confidencePct =
    draft?.confidence != null
      ? `${(draft.confidence * 100).toFixed(0)}%`
      : null;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <header>
        <DisplayLg>Review giao dịch từ OCR</DisplayLg>
        <p className="text-body-sm text-body mt-1">
          Receipt #{receiptId} · Provider: {draft?.provider ?? "-"}
          {confidencePct ? (
            <>
              {" "}
              · Confidence:{" "}
              <span
                className={
                  isLowConfidence
                    ? "font-semibold text-accent-red"
                    : "font-semibold text-accent-green"
                }
              >
                {confidencePct}
              </span>
            </>
          ) : null}
        </p>
      </header>

      {isLowConfidence ? (
        <CalloutBanner severity="warning">
          OCR confidence thấp. Vui lòng kiểm tra kỹ các field trước khi lưu.
        </CalloutBanner>
      ) : null}

      <Card>
        <form onSubmit={onSubmit} className="grid gap-4 md:grid-cols-2">
          <label className="text-body-xs text-ink md:col-span-2">
            Merchant
            <Input
              type="text"
              value={form.merchantName}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, merchantName: event.target.value }))
              }
              placeholder="VD: Highland Coffee"
              className={`mt-1.5 ${
                isLowConfidence ? "border-accent-red/50" : ""
              }`}
            />
          </label>

          <label className="text-body-xs text-ink">
            Số tiền
            <Input
              type="text"
              inputMode="decimal"
              required
              value={form.amount}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, amount: event.target.value }))
              }
              placeholder="VD: 75000"
              className={`mt-1.5 ${
                isLowConfidence ? "border-accent-red/50" : ""
              }`}
            />
          </label>

          <label className="text-body-xs text-ink">
            Tiền tệ
            <Input
              type="text"
              value={form.currency}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, currency: event.target.value }))
              }
              maxLength={10}
              className="mt-1.5"
            />
          </label>

          <label className="text-body-xs text-ink">
            Ngày giao dịch
            <Input
              type="date"
              required
              value={form.transactionDate}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, transactionDate: event.target.value }))
              }
              className={`mt-1.5 ${
                isLowConfidence ? "border-accent-red/50" : ""
              }`}
            />
          </label>

          <label className="text-body-xs text-ink">
            Danh mục
            <select
              value={form.categoryId}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, categoryId: event.target.value }))
              }
              className="mt-1.5 w-full h-9 rounded-md border border-hairline bg-surface-card px-3 text-body-md text-ink focus:outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
            >
              <option value="">— Chưa phân loại —</option>
              {categories.map((category) => (
                <option key={category.id} value={String(category.id)}>
                  {category.name}
                  {category.is_system ? "" : " (custom)"}
                </option>
              ))}
            </select>
          </label>

          <label className="text-body-xs text-ink md:col-span-2">
            Ghi chú
            <Textarea
              value={form.note}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, note: event.target.value }))
              }
              rows={3}
              maxLength={1000}
              className="mt-1.5"
            />
          </label>

          {submitError ? (
            <div className="md:col-span-2">
              <CalloutBanner severity="warning">{submitError}</CalloutBanner>
            </div>
          ) : null}

          <div className="flex items-center gap-2 md:col-span-2">
            <Button type="submit" variant="primary" disabled={submitting}>
              {submitting ? "Đang lưu..." : "Lưu giao dịch"}
            </Button>
            <Link href="/receipts/upload">
              <Button type="button" variant="secondary">
                Hủy
              </Button>
            </Link>
          </div>
        </form>
      </Card>

      {/* Invoice Details Section */}
      {invoice ? (
        <Card>
          <div className="space-y-4">
            <h2 className="text-body-md font-semibold text-ink">Chi tiết hóa đơn điện tử</h2>

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
              <h3 className="text-body-xs font-semibold text-mute uppercase mb-2">Người bán</h3>
              <div className="grid gap-1 text-body-sm">
                <div><span className="text-mute">Tên:</span> {invoice.seller_name ?? <span className="text-mute italic">—</span>}</div>
                <div><span className="text-mute">MST:</span> {invoice.seller_tax_id ?? <span className="text-mute italic">—</span>}</div>
                <div><span className="text-mute">Địa chỉ:</span> {invoice.seller_address ?? <span className="text-mute italic">—</span>}</div>
              </div>
            </div>

            {/* Buyer */}
            <div className="border-t border-hairline pt-3">
              <h3 className="text-body-xs font-semibold text-mute uppercase mb-2">Người mua</h3>
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
                <h3 className="text-body-xs font-semibold text-mute uppercase mb-2">Chi tiết hàng hóa / dịch vụ</h3>
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
              <h3 className="text-body-xs font-semibold text-mute uppercase mb-2">Tổng cộng</h3>
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
                <h3 className="text-body-xs font-semibold text-mute uppercase mb-2">Xác thực</h3>
                <div className="grid gap-1 text-body-sm">
                  {invoice.signing_date ? <div><span className="text-mute">Ngày ký:</span> {invoice.signing_date}</div> : null}
                  {invoice.digital_signature ? <div><span className="text-mute">Chữ ký số:</span> <span className="text-accent-green">✓ Có</span></div> : null}
                  {invoice.lookup_link ? <div><span className="text-mute">Tra cứu:</span> <a href={invoice.lookup_link} target="_blank" rel="noopener noreferrer" className="text-link-teal hover:underline">{invoice.lookup_link}</a></div> : null}
                </div>
              </div>
            ) : null}
          </div>
        </Card>
      ) : null}

      {draft?.raw_text ? (
        <details className="rounded-md border border-hairline bg-surface-dark p-4 text-body-sm text-on-dark">
          <summary className="cursor-pointer font-semibold">
            Xem text OCR gốc
          </summary>
          <pre className="mt-3 overflow-x-auto whitespace-pre-wrap font-mono text-caption-sm text-on-dark/90">
            {draft.raw_text}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
