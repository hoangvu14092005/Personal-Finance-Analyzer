"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { getMe } from "@/lib/auth-api";
import { Category, listCategories } from "@/lib/categories-api";
import {
  Budget,
  BudgetUsage,
  createBudget,
  deleteBudget,
  getBudgetUsage,
  listBudgets,
  updateBudget,
} from "@/lib/budgets-api";

type FormState = {
  categoryId: string;
  periodMonth: string;
  amount: string;
};

function currentPeriodMonth(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

function formatVnd(value: string): string {
  // Server trả decimal string (vd "1000000.00"). Hiển thị có dấu phẩy,
  // bỏ phần thập phân = 0 để VND nhìn gọn.
  const num = Number(value);
  if (!Number.isFinite(num)) return value;
  return num.toLocaleString("vi-VN", { maximumFractionDigits: 0 });
}

function statusBadgeClass(status: BudgetUsage["status"]): string {
  switch (status) {
    case "exceeded":
      return "bg-rose-100 text-rose-800 border-rose-200";
    case "warning":
      return "bg-amber-100 text-amber-800 border-amber-200";
    case "safe":
    default:
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
  }
}

function statusLabel(status: BudgetUsage["status"]): string {
  switch (status) {
    case "exceeded":
      return "Vượt ngân sách";
    case "warning":
      return "Sắp vượt";
    case "safe":
    default:
      return "An toàn";
  }
}

function progressBarColor(status: BudgetUsage["status"]): string {
  switch (status) {
    case "exceeded":
      return "bg-rose-500";
    case "warning":
      return "bg-amber-500";
    case "safe":
    default:
      return "bg-emerald-500";
  }
}

export default function BudgetsClient() {
  const router = useRouter();

  const [authReady, setAuthReady] = useState(false);
  const [period, setPeriod] = useState(currentPeriodMonth());

  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [usages, setUsages] = useState<BudgetUsage[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [form, setForm] = useState<FormState>({
    categoryId: "",
    periodMonth: currentPeriodMonth(),
    amount: "",
  });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Auth gate.
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

  const loadData = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [budgetList, usageList, categoryList] = await Promise.all([
        listBudgets(period),
        getBudgetUsage(period),
        listCategories(),
      ]);
      setBudgets(budgetList.items);
      setUsages(usageList);
      setCategories(categoryList.items);
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Không tải được dữ liệu ngân sách.",
      );
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    if (!authReady) return;
    void loadData();
  }, [authReady, loadData]);

  const categoryMap = useMemo(() => {
    const map = new Map<number, Category>();
    for (const cat of categories) map.set(cat.id, cat);
    return map;
  }, [categories]);

  // Map budget_id → usage để render thông tin trong list.
  const usageByBudgetId = useMemo(() => {
    const map = new Map<number, BudgetUsage>();
    for (const u of usages) map.set(u.budget_id, u);
    return map;
  }, [usages]);

  const resetForm = () => {
    setForm({
      categoryId: "",
      periodMonth: period,
      amount: "",
    });
    setEditingId(null);
    setSubmitError(null);
  };

  const startEdit = (budget: Budget) => {
    setEditingId(budget.id);
    setForm({
      categoryId: String(budget.category_id),
      periodMonth: budget.period_month,
      amount: budget.amount,
    });
    setSubmitError(null);
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    const trimmedAmount = form.amount.trim();
    const numericAmount = Number(trimmedAmount);
    if (!trimmedAmount || !Number.isFinite(numericAmount) || numericAmount <= 0) {
      setSubmitError("Số tiền phải là số dương.");
      return;
    }

    const periodPattern = /^\d{4}-(0[1-9]|1[0-2])$/;
    if (!periodPattern.test(form.periodMonth)) {
      setSubmitError("Tháng phải có dạng YYYY-MM (vd: 2026-05).");
      return;
    }

    setSubmitting(true);
    try {
      if (editingId !== null) {
        await updateBudget(editingId, { amount: trimmedAmount });
      } else {
        if (!form.categoryId) {
          setSubmitError("Cần chọn danh mục.");
          setSubmitting(false);
          return;
        }
        await createBudget({
          category_id: Number(form.categoryId),
          period_month: form.periodMonth,
          amount: trimmedAmount,
        });
      }
      // Nếu user tạo budget cho tháng khác với period filter → đổi filter
      // sang tháng đó để họ thấy ngay.
      const nextPeriod = editingId === null ? form.periodMonth : period;
      resetForm();
      if (nextPeriod !== period) {
        setPeriod(nextPeriod);
      } else {
        await loadData();
      }
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Lưu ngân sách thất bại.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const onDelete = async (budget: Budget) => {
    const cat = categoryMap.get(budget.category_id);
    const label = cat?.name ?? `#${budget.category_id}`;
    if (!confirm(`Xoá ngân sách ${label} tháng ${budget.period_month}?`)) return;

    try {
      await deleteBudget(budget.id);
      if (editingId === budget.id) resetForm();
      await loadData();
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Xoá ngân sách thất bại.",
      );
    }
  };

  if (!authReady) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-sm text-slate-600">Đang xác thực phiên đăng nhập...</p>
      </section>
    );
  }

  const isEditing = editingId !== null;

  return (
    <section className="space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Ngân sách</h1>
          <p className="text-sm text-slate-600">
            Đặt ngưỡng chi tiêu theo danh mục và theo dõi mức sử dụng trong tháng.
          </p>
        </div>
        <label className="text-sm font-medium text-slate-700">
          Tháng
          <input
            type="month"
            value={period}
            onChange={(event) => setPeriod(event.target.value || currentPeriodMonth())}
            className="ml-2 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
          />
        </label>
      </header>

      {loadError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {loadError}
        </div>
      ) : null}

      <form
        onSubmit={onSubmit}
        className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:grid-cols-4"
      >
        <label className="text-sm font-medium text-slate-700 md:col-span-2">
          Danh mục
          <select
            value={form.categoryId}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, categoryId: event.target.value }))
            }
            disabled={isEditing}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:bg-slate-100 disabled:opacity-70"
          >
            <option value="">— Chọn danh mục —</option>
            {categories.map((category) => (
              <option key={category.id} value={String(category.id)}>
                {category.name}
                {category.is_system ? "" : " (custom)"}
              </option>
            ))}
          </select>
          {isEditing ? (
            <span className="mt-1 block text-xs text-slate-500">
              Không đổi được khi sửa — xoá và tạo lại nếu cần.
            </span>
          ) : null}
        </label>

        <label className="text-sm font-medium text-slate-700">
          Tháng (YYYY-MM)
          <input
            type="month"
            value={form.periodMonth}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                periodMonth: event.target.value || currentPeriodMonth(),
              }))
            }
            disabled={isEditing}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:opacity-70"
          />
        </label>

        <label className="text-sm font-medium text-slate-700">
          Số tiền (VND)
          <input
            type="text"
            inputMode="decimal"
            required
            value={form.amount}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, amount: event.target.value }))
            }
            placeholder="VD: 2000000"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        {submitError ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 md:col-span-4">
            {submitError}
          </div>
        ) : null}

        <div className="flex items-center gap-2 md:col-span-4">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Đang lưu..." : isEditing ? "Cập nhật" : "Thêm ngân sách"}
          </button>
          {isEditing ? (
            <button
              type="button"
              onClick={resetForm}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              Huỷ sửa
            </button>
          ) : null}
        </div>
      </form>

      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-slate-900">
            Ngân sách tháng {period}
          </h2>
          <p className="text-xs text-slate-500">
            Sắp xếp theo % sử dụng giảm dần.
          </p>
        </div>

        {loading ? (
          <div className="px-6 py-8 text-sm text-slate-500">Đang tải…</div>
        ) : budgets.length === 0 ? (
          <div className="px-6 py-8 text-sm text-slate-500">
            Chưa có ngân sách nào cho tháng này. Hãy thêm phía trên.
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {/* Sort theo usage DESC; budget không có usage (0%) đẩy cuối. */}
            {[...budgets]
              .sort((a, b) => {
                const ua = usageByBudgetId.get(a.id)?.percent_used ?? 0;
                const ub = usageByBudgetId.get(b.id)?.percent_used ?? 0;
                return ub - ua;
              })
              .map((budget) => {
                const cat = categoryMap.get(budget.category_id);
                const usage = usageByBudgetId.get(budget.id);
                const name = cat?.name ?? `Category #${budget.category_id}`;
                const percent = usage?.percent_used ?? 0;
                const barWidth = Math.min(100, percent);
                const status = usage?.status ?? "safe";

                return (
                  <li
                    key={budget.id}
                    className="flex flex-col gap-3 px-6 py-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-3">
                        {cat?.color ? (
                          <span
                            aria-hidden
                            className="h-3 w-3 rounded-full"
                            style={{ backgroundColor: cat.color }}
                          />
                        ) : null}
                        <span className="text-sm font-semibold text-slate-900">
                          {name}
                        </span>
                        <span
                          className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClass(
                            status,
                          )}`}
                        >
                          {statusLabel(status)}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-slate-600">
                        <span>
                          Đã dùng:{" "}
                          <strong className="text-slate-900">
                            {formatVnd(usage?.spent_amount ?? "0")}
                          </strong>
                        </span>
                        <span>/</span>
                        <span>
                          Ngân sách:{" "}
                          <strong className="text-slate-900">
                            {formatVnd(budget.amount)}
                          </strong>
                        </span>
                        <span className="ml-auto font-medium text-slate-800">
                          {percent.toFixed(0)}%
                        </span>
                      </div>

                      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                        <div
                          className={`h-full rounded-full transition-all ${progressBarColor(
                            status,
                          )}`}
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>

                      {usage ? (
                        <div className="text-xs text-slate-500">
                          Còn lại:{" "}
                          <span
                            className={
                              Number(usage.remaining_amount) < 0
                                ? "font-semibold text-rose-600"
                                : "font-semibold text-emerald-600"
                            }
                          >
                            {formatVnd(usage.remaining_amount)}
                          </span>
                        </div>
                      ) : null}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => startEdit(budget)}
                        className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                      >
                        Sửa
                      </button>
                      <button
                        type="button"
                        onClick={() => void onDelete(budget)}
                        className="rounded-lg border border-rose-300 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50"
                      >
                        Xoá
                      </button>
                    </div>
                  </li>
                );
              })}
          </ul>
        )}
      </div>
    </section>
  );
}
