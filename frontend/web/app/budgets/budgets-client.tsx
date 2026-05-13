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
import {
  Badge,
  Button,
  CalloutBanner,
  Card,
  DisplayLg,
  Input,
} from "@/components/ui";

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
  const num = Number(value);
  if (!Number.isFinite(num)) return value;
  return num.toLocaleString("vi-VN", { maximumFractionDigits: 0 });
}

type BudgetStatus = BudgetUsage["status"];

function statusTone(status: BudgetStatus): "green" | "purple" | "red" {
  switch (status) {
    case "exceeded":
      return "red";
    case "warning":
      return "purple";
    default:
      return "green";
  }
}

function statusLabel(status: BudgetStatus): string {
  switch (status) {
    case "exceeded":
      return "Vượt ngân sách";
    case "warning":
      return "Sắp vượt";
    default:
      return "An toàn";
  }
}

function progressBarColor(status: BudgetStatus): string {
  switch (status) {
    case "exceeded":
      return "bg-accent-red";
    case "warning":
      return "bg-accent-purple";
    default:
      return "bg-accent-green";
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
      <Card>
        <p className="text-body-sm text-mute">Đang xác thực phiên đăng nhập...</p>
      </Card>
    );
  }

  const isEditing = editingId !== null;

  return (
    <div className="space-y-6">
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <DisplayLg>Ngân sách</DisplayLg>
          <p className="text-body-sm text-body mt-1">
            Đặt ngưỡng chi tiêu theo danh mục và theo dõi mức sử dụng trong tháng.
          </p>
        </div>
        <label className="text-body-xs text-ink flex items-center gap-2">
          Tháng
          <Input
            type="month"
            value={period}
            onChange={(event) => setPeriod(event.target.value || currentPeriodMonth())}
            className="w-auto"
          />
        </label>
      </header>

      {loadError ? (
        <CalloutBanner severity="warning">{loadError}</CalloutBanner>
      ) : null}

      <Card>
        <form onSubmit={onSubmit} className="grid gap-4 md:grid-cols-4">
          <label className="text-body-xs text-ink md:col-span-2">
            Danh mục
            <select
              value={form.categoryId}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, categoryId: event.target.value }))
              }
              disabled={isEditing}
              className="mt-1.5 w-full h-9 rounded-md border border-hairline bg-surface-card px-3 text-body-md text-ink focus:outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20 disabled:bg-surface-soft disabled:text-ash"
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
              <span className="mt-1 block text-caption-sm text-mute">
                Không đổi được khi sửa — xoá và tạo lại nếu cần.
              </span>
            ) : null}
          </label>

          <label className="text-body-xs text-ink">
            Tháng (YYYY-MM)
            <Input
              type="month"
              value={form.periodMonth}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  periodMonth: event.target.value || currentPeriodMonth(),
                }))
              }
              disabled={isEditing}
              className="mt-1.5"
            />
          </label>

          <label className="text-body-xs text-ink">
            Số tiền (VND)
            <Input
              type="text"
              inputMode="decimal"
              required
              value={form.amount}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, amount: event.target.value }))
              }
              placeholder="VD: 2000000"
              className="mt-1.5"
            />
          </label>

          {submitError ? (
            <div className="md:col-span-4">
              <CalloutBanner severity="warning">{submitError}</CalloutBanner>
            </div>
          ) : null}

          <div className="flex items-center gap-2 md:col-span-4">
            <Button type="submit" variant="primary" disabled={submitting}>
              {submitting ? "Đang lưu..." : isEditing ? "Cập nhật" : "Thêm ngân sách"}
            </Button>
            {isEditing ? (
              <Button type="button" variant="secondary" onClick={resetForm}>
                Huỷ sửa
              </Button>
            ) : null}
          </div>
        </form>
      </Card>

      <Card className="p-0 overflow-hidden">
        <div className="border-b border-hairline-soft px-6 py-4">
          <h2 className="text-heading-md text-ink">Ngân sách tháng {period}</h2>
          <p className="text-caption-sm text-mute mt-1">
            Sắp xếp theo % sử dụng giảm dần.
          </p>
        </div>

        {loading ? (
          <div className="px-6 py-8 text-body-sm text-mute">Đang tải…</div>
        ) : budgets.length === 0 ? (
          <div className="px-6 py-8 text-body-sm text-mute">
            Chưa có ngân sách nào cho tháng này. Hãy thêm phía trên.
          </div>
        ) : (
          <ul className="divide-y divide-hairline-soft">
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
                      <div className="flex items-center gap-3 flex-wrap">
                        {cat?.color ? (
                          <span
                            aria-hidden
                            className="h-3 w-3 rounded-full"
                            style={{ backgroundColor: cat.color }}
                          />
                        ) : null}
                        <span className="text-body-strong text-ink">{name}</span>
                        <Badge tone={statusTone(status)}>
                          {statusLabel(status)}
                        </Badge>
                      </div>

                      <div className="flex items-center gap-3 text-caption-sm text-body flex-wrap">
                        <span>
                          Đã dùng:{" "}
                          <strong className="text-ink">
                            {formatVnd(usage?.spent_amount ?? "0")}
                          </strong>
                        </span>
                        <span className="text-ash">/</span>
                        <span>
                          Ngân sách:{" "}
                          <strong className="text-ink">
                            {formatVnd(budget.amount)}
                          </strong>
                        </span>
                        <span className="ml-auto font-semibold text-ink">
                          {percent.toFixed(0)}%
                        </span>
                      </div>

                      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-soft">
                        <div
                          className={`h-full rounded-full transition-all ${progressBarColor(status)}`}
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>

                      {usage ? (
                        <div className="text-caption-sm text-mute">
                          Còn lại:{" "}
                          <span
                            className={
                              Number(usage.remaining_amount) < 0
                                ? "font-semibold text-accent-red"
                                : "font-semibold text-accent-green"
                            }
                          >
                            {formatVnd(usage.remaining_amount)}
                          </span>
                        </div>
                      ) : null}
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => startEdit(budget)}
                      >
                        Sửa
                      </Button>
                      <Button
                        type="button"
                        variant="danger"
                        size="sm"
                        onClick={() => void onDelete(budget)}
                      >
                        Xoá
                      </Button>
                    </div>
                  </li>
                );
              })}
          </ul>
        )}
      </Card>
    </div>
  );
}
