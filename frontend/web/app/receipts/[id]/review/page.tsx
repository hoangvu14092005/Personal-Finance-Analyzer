"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, use, useEffect, useMemo, useState } from "react";

import { getMe } from "@/lib/auth-api";
import { Category, listCategories } from "@/lib/categories-api";
import { DraftReview, getReceiptDraft } from "@/lib/receipts-api";
import { createTransaction } from "@/lib/transactions-api";

type ReviewFormState = {
  merchantName: string;
  amount: string;
  currency: string;
  transactionDate: string;
  categoryId: string; // empty string = none
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
  // Next.js 15 dynamic route params là Promise; React 19 `use()` unwrap.
  const { id } = use(params);
  const receiptId = Number(id);
  const router = useRouter();

  const [authReady, setAuthReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftReview | null>(null);
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
      <section className="rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-sm text-slate-600">Đang xác thực phiên đăng nhập...</p>
      </section>
    );
  }

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-sm text-slate-600">Đang tải dữ liệu OCR draft...</p>
      </section>
    );
  }

  if (loadError) {
    return (
      <section className="space-y-4 rounded-2xl border border-amber-200 bg-amber-50 p-8 text-amber-900">
        <h1 className="text-xl font-semibold">Không tải được draft</h1>
        <p className="text-sm">{loadError}</p>
        <p className="text-sm">
          Bạn có thể chờ OCR hoàn thành rồi tải lại trang, hoặc{" "}
          <Link
            href="/transactions/new"
            className="font-semibold text-amber-700 underline hover:text-amber-900"
          >
            nhập tay
          </Link>
          .
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Review giao dịch từ OCR</h1>
        <p className="text-sm text-slate-600">
          Receipt #{receiptId} · Provider: {draft?.provider ?? "-"}
          {draft?.confidence !== null && draft?.confidence !== undefined ? (
            <>
              {" "}
              · Confidence:{" "}
              <span
                className={
                  isLowConfidence
                    ? "font-semibold text-amber-700"
                    : "font-semibold text-emerald-700"
                }
              >
                {(draft.confidence * 100).toFixed(0)}%
              </span>
            </>
          ) : null}
        </p>
      </header>

      {isLowConfidence ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          OCR confidence thấp. Vui lòng kiểm tra kỹ các field trước khi lưu.
        </div>
      ) : null}

      <form
        onSubmit={onSubmit}
        className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:grid-cols-2"
      >
        <label className="text-sm font-medium text-slate-700 md:col-span-2">
          Merchant
          <input
            type="text"
            value={form.merchantName}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, merchantName: event.target.value }))
            }
            placeholder="VD: Highlands Coffee"
            className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
              isLowConfidence ? "border-amber-300" : "border-slate-300"
            }`}
          />
        </label>

        <label className="text-sm font-medium text-slate-700">
          Số tiền
          <input
            type="text"
            inputMode="decimal"
            required
            value={form.amount}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, amount: event.target.value }))
            }
            placeholder="VD: 75000"
            className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
              isLowConfidence ? "border-amber-300" : "border-slate-300"
            }`}
          />
        </label>

        <label className="text-sm font-medium text-slate-700">
          Tiền tệ
          <input
            type="text"
            value={form.currency}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, currency: event.target.value }))
            }
            maxLength={10}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        <label className="text-sm font-medium text-slate-700">
          Ngày giao dịch
          <input
            type="date"
            required
            value={form.transactionDate}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, transactionDate: event.target.value }))
            }
            className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
              isLowConfidence ? "border-amber-300" : "border-slate-300"
            }`}
          />
        </label>

        <label className="text-sm font-medium text-slate-700">
          Danh mục
          <select
            value={form.categoryId}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, categoryId: event.target.value }))
            }
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
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

        <label className="text-sm font-medium text-slate-700 md:col-span-2">
          Ghi chú
          <textarea
            value={form.note}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, note: event.target.value }))
            }
            rows={3}
            maxLength={1000}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        {submitError ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 md:col-span-2">
            {submitError}
          </div>
        ) : null}

        <div className="flex items-center gap-2 md:col-span-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Đang lưu..." : "Lưu giao dịch"}
          </button>
          <Link
            href="/receipts/upload"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          >
            Hủy
          </Link>
        </div>
      </form>

      {draft?.raw_text ? (
        <details className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
          <summary className="cursor-pointer font-semibold">
            Xem text OCR gốc
          </summary>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded bg-white p-3 text-xs">
            {draft.raw_text}
          </pre>
        </details>
      ) : null}
    </section>
  );
}
