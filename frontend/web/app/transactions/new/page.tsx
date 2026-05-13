"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { getMe } from "@/lib/auth-api";
import { Category, listCategories } from "@/lib/categories-api";
import { createTransaction } from "@/lib/transactions-api";
import {
  Button,
  CalloutBanner,
  Card,
  DisplayLg,
  Input,
  Textarea,
} from "@/components/ui";

type ManualFormState = {
  merchantName: string;
  amount: string;
  currency: string;
  transactionDate: string;
  categoryId: string;
  note: string;
};

function defaultDate(): string {
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
      <Card>
        <p className="text-body-sm text-mute">Đang xác thực phiên đăng nhập...</p>
      </Card>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <header>
        <DisplayLg>Nhập giao dịch thủ công</DisplayLg>
        <p className="text-body-sm text-body mt-1">
          Dùng form này khi không có hóa đơn cần OCR.
        </p>
      </header>

      {categoriesError ? (
        <CalloutBanner severity="note">{categoriesError}</CalloutBanner>
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
              placeholder="VD: Grab, Highland, ..."
              className="mt-1.5"
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
              placeholder="VD: 50000"
              className="mt-1.5"
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
              className="mt-1.5"
            />
          </label>

          <label className="text-body-xs text-ink">
            Danh mục
            <select
              value={form.categoryId}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, categoryId: event.target.value }))
              }
              disabled={categoriesLoading}
              className="mt-1.5 w-full h-9 rounded-md border border-hairline bg-surface-card px-3 text-body-md text-ink focus:outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20 disabled:opacity-50"
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
            <Link href="/transactions">
              <Button type="button" variant="secondary">
                Hủy
              </Button>
            </Link>
          </div>
        </form>
      </Card>
    </div>
  );
}
