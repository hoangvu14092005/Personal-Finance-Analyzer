import { apiBaseUrl } from "@/lib/config";

// Server trả `amount`/`spent_amount`/... dưới dạng decimal string (Pydantic
// Decimal). Giữ string ở FE để tránh mất precision; format khi render.

export type Budget = {
  id: number;
  user_id: number;
  category_id: number;
  period_month: string; // YYYY-MM
  amount: string;
  created_at: string;
  updated_at: string;
};

export type BudgetListResponse = {
  items: Budget[];
};

export type BudgetCreatePayload = {
  category_id: number;
  period_month: string;
  amount: string;
};

export type BudgetUpdatePayload = {
  amount: string;
};

export type BudgetStatus = "safe" | "warning" | "exceeded";

export type BudgetUsage = {
  budget_id: number;
  category_id: number;
  category_name: string;
  category_color: string | null;
  period_month: string;
  budget_amount: string;
  spent_amount: string;
  remaining_amount: string;
  percent_used: number;
  status: BudgetStatus;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      // Non-JSON body; keep null.
    }
  }

  if (!response.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Request failed with status ${response.status}`;
    throw new Error(detail);
  }

  return body as T;
}

export async function listBudgets(periodMonth?: string): Promise<BudgetListResponse> {
  const query = periodMonth ? `?period_month=${encodeURIComponent(periodMonth)}` : "";
  return request<BudgetListResponse>(`/api/v1/budgets${query}`, { method: "GET" });
}

export async function createBudget(payload: BudgetCreatePayload): Promise<Budget> {
  return request<Budget>("/api/v1/budgets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateBudget(
  id: number,
  payload: BudgetUpdatePayload,
): Promise<Budget> {
  return request<Budget>(`/api/v1/budgets/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteBudget(id: number): Promise<void> {
  await request<void>(`/api/v1/budgets/${id}`, { method: "DELETE" });
}

export async function getBudgetUsage(periodMonth: string): Promise<BudgetUsage[]> {
  const query = `?period_month=${encodeURIComponent(periodMonth)}`;
  return request<BudgetUsage[]>(`/api/v1/budgets/usage${query}`, { method: "GET" });
}
