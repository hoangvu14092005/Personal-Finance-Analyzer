"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, use, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  FileText,
  ReceiptText,
  Save,
  Sparkles,
  UploadCloud,
  type LucideIcon,
} from "lucide-react";

import { getMe } from "@/lib/auth-api";
import { Category, listCategories } from "@/lib/categories-api";
import {
  confirmReceipt,
  DraftReview,
  getReceiptDraft,
  getReceiptInvoice,
  InvoiceData,
} from "@/lib/receipts-api";
import {
  Badge,
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

function formatMoney(value: string | null | undefined, currency = "VND"): string {
  if (!value) return "-";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return `${value} ${currency}`;
  return `${numeric.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} ${currency}`;
}

function confidenceTone(confidence: number | null | undefined): "green" | "red" | "neutral" {
  if (confidence == null) return "neutral";
  return confidence < LOW_CONFIDENCE_THRESHOLD ? "red" : "green";
}

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
      const confirmed = await confirmReceipt(receiptId, {
        amount: trimmedAmount,
        currency: form.currency.trim().toUpperCase() || "VND",
        transaction_date: form.transactionDate,
        merchant_name: form.merchantName.trim() || null,
        category_id: form.categoryId ? Number(form.categoryId) : null,
        note: form.note.trim() || null,
      });
      router.push(`/transactions?created=${confirmed.transaction_id}`);
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
    <div className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <DisplayLg>Kết quả quét thông tin</DisplayLg>
            <p className="mt-0.5 text-sm text-ash">
              Kiểm tra dữ liệu OCR của hóa đơn #{receiptId}, chỉnh lại nếu cần rồi đồng bộ vào sổ ví.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/receipts">
              <Button type="button" variant="secondary" size="sm"><ReceiptText className="h-4 w-4" aria-hidden />Danh sách hóa đơn</Button>
            </Link>
            <Link href="/receipts/upload">
              <Button type="button" variant="secondary" size="sm"><UploadCloud className="h-4 w-4" aria-hidden />Tải hóa đơn khác</Button>
            </Link>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <ReviewStat icon={Sparkles} label="Bộ máy OCR" value={draft?.provider ?? "-"} detail="Đang xử lý bóc tách" tone="neutral" />
          <ReviewStat icon={isLowConfidence ? AlertTriangle : CheckCircle} label="Confidence" value={confidencePct ?? "-"} detail={isLowConfidence ? "Cần kiểm tra kỹ" : "Đủ tốt để review"} tone={confidenceTone(draft?.confidence)} />
          <ReviewStat icon={ReceiptText} label="Tổng hóa đơn" value={formatMoney(draft?.amount, draft?.currency ?? "VND")} detail="Chờ bạn xác nhận" tone="blue" />
          <ReviewStat icon={FileText} label="Dòng sản phẩm" value={String(draft?.line_items.length ?? 0)} detail={invoice ? "Có dữ liệu VAT" : "Hóa đơn thường"} tone="purple" />
        </div>
      </header>

      {isLowConfidence ? (
        <CalloutBanner severity="warning">
          OCR confidence thấp. Vui lòng kiểm tra kỹ các field trước khi lưu.
        </CalloutBanner>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-12">
        <section className="space-y-4 xl:col-span-5">
          <Card className="border-hairline-soft bg-surface-card">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Mô phỏng tệp hóa đơn</p>
                <h2 className="mt-1 text-heading-sm-mixed text-ink">Dữ liệu OCR đọc được</h2>
              </div>
              <Badge tone={draft?.linked_transaction ? "green" : "blue"}>
                {draft?.linked_transaction ? `Giao dịch #${draft.linked_transaction.transaction_id}` : "Chưa ghi sổ"}
              </Badge>
            </div>

            <div className="mt-5 rounded-xl border border-hairline-soft bg-surface-doc p-4">
              <div className="border-b border-dashed border-hairline-soft pb-4 text-center">
                <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Đơn vị cung cấp</p>
                <p className="mt-1 text-heading-sm-mixed text-ink">{draft?.merchant_name ?? "Chưa nhận diện"}</p>
                <p className="mt-1 text-caption-sm text-mute">Ngày giao dịch gợi ý: {draft?.transaction_date ?? "-"}</p>
              </div>

              <div className="space-y-3 border-b border-dashed border-hairline-soft py-4">
                {draft?.line_items.length ? (
                  draft.line_items.map((item) => (
                    <div key={item.id} className="flex items-start justify-between gap-3 text-body-sm">
                      <div className="min-w-0">
                        <p className="truncate font-semibold text-ink">{item.item_name}</p>
                        <p className="text-caption-sm text-mute">SL {item.quantity} x {formatMoney(item.unit_price, draft.currency ?? "VND")}</p>
                      </div>
                      <p className="shrink-0 font-bold text-ink">{formatMoney(item.total_price, draft.currency ?? "VND")}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-body-sm text-mute">OCR chưa tách được line items. Vẫn có thể xác nhận giao dịch tổng nếu số tiền/ngày đúng.</p>
                )}
              </div>

              <div className="flex items-center justify-between pt-4">
                <span className="text-caption-xs font-bold uppercase tracking-wide text-mute">Tổng OCR</span>
                <span className="text-xl font-black text-accent-red">{formatMoney(draft?.amount, draft?.currency ?? "VND")}</span>
              </div>
            </div>
          </Card>

          <Card className="border-hairline-soft bg-surface-card">
            <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Cơ chế đồng bộ</p>
            <p className="mt-2 text-body-sm text-body">
              Sửa các trường bóc tách sai trước khi bấm xác nhận để ghi vào sổ ví.
            </p>
          </Card>
        </section>

        <section className="space-y-4 xl:col-span-7">
          <Card className="border-hairline-soft bg-surface-card">
            <div className="mb-5 flex items-start justify-between gap-3">
              <div>
                <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">Ghi sổ giao dịch</p>
                <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
                  <Save className="h-4.5 w-4.5 text-mute" aria-hidden />
                  Thông tin sẽ đồng bộ vào sổ ví
                </h2>
              </div>
              <Badge tone="green">Sẵn sàng ghi sổ</Badge>
            </div>

            <form onSubmit={onSubmit} className="grid gap-4 md:grid-cols-2">
              <label className="text-body-xs text-ink md:col-span-2">
                Đơn vị cung cấp
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

              <div className="flex flex-wrap items-center gap-2 md:col-span-2">
                <Button type="submit" variant="primary" disabled={submitting}>
                  {submitting ? "Đang lưu..." : <><Save className="h-4 w-4" aria-hidden />Lưu giao dịch</>}
                </Button>
                <Link href="/receipts/upload">
                  <Button type="button" variant="secondary">Hủy</Button>
                </Link>
              </div>
            </form>
          </Card>
        </section>
      </div>

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

function ReviewStat({ icon: Icon, label, value, detail, tone }: { icon: LucideIcon; label: string; value: string; detail: string; tone: "neutral" | "green" | "red" | "blue" | "purple" }) {
  const toneClass = {
    neutral: "bg-surface-doc text-ink",
    green: "bg-accent-green-soft text-accent-green",
    red: "bg-accent-red-soft text-accent-red",
    blue: "bg-accent-blue-soft text-link-blue",
    purple: "bg-accent-purple-soft text-accent-purple",
  }[tone];
  return (
    <article className="rounded-xl border border-hairline-soft bg-surface-doc p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">{label}</p>
          <p className="mt-2 truncate text-xl font-black text-ink">{value}</p>
        </div>
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${toneClass}`}>
          <Icon className="h-4.5 w-4.5" aria-hidden />
        </span>
      </div>
      <p className="mt-2 text-caption-sm text-mute">{detail}</p>
    </article>
  );
}
