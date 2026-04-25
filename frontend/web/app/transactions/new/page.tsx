"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { getMe } from "@/lib/auth-api";
import { Category, listCategories } from "@/lib/categories-api";
import { createTransaction } from "@/lib/transactions-api";

type ManualFormState = {
  merchantName: string;
  amount: string;
  currency: string;
  transactionDate: string;
  categoryId: string;
  note: string;
};

function defaultDate(): string {
  // Ngày local hôm nay theo format YYYY-MM-DD; tránh lệch timezone qua UTC.
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export default function ManualEntryPage() {
  const router = useRouter();

  const [authReady, setAuthReady] = useState(false);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);

  const [form, setForm] = useState<ManualFormState>({
    merchantName: "",
    amount: "",
    currency: "VND",
    transactionDate: defaultDate(),
    categoryId: "",
    note: "",
  });
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
    let cancelled = false;
    (async () => {
      setCategoriesLoading(true);
      setCategoriesError(null);
      try {
        const response = await listCategories();
        if (!cancelled) setCategories(response.items);
      } catch (error) {
        if (!cancelled) {
          setCategoriesError(
            error instanceof Error
              ? error.message
              : "Không tải được danh mục.",
          );
        }
      } finally {
        if (!cancelled) setCategoriesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authReady]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    const trimmedAmount = form.amount.trim();
    if (!trimmedAmount) {
      setSubmitError("Số tiền là bắt buộc.");
      return;
    }
    const numericAmount = Number(trimmedAmount);
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      setSubmitError("Số tiền phải là số dương.");
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

  return (
    <section className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Nhập giao dịch thủ công</h1>
        <p className="text-sm text-slate-600">
          Dùng form này khi không có hóa đơn cần OCR.
        </p>
      </header>

      {categoriesError ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {categoriesError}
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
            placeholder="VD: Grab, Highlands, ..."
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
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
            placeholder="VD: 50000"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
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
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        <label className="text-sm font-medium text-slate-700">
          Danh mục
          <select
            value={form.categoryId}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, categoryId: event.target.value }))
            }
            disabled={categoriesLoading}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:opacity-50"
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
            href="/transactions"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          >
            Hủy
          </Link>
        </div>
      </form>
    </section>
  );
}
