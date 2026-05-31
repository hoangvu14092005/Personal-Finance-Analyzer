import { expect, test, type Page } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser, mockCategories } from "./helpers";

const now = "2026-05-29T08:00:00Z";

/** Mock every API a screen may call so navigation never hangs on network. */
async function mockEverything(page: Page) {
  const api = backendBaseUrl();
  await mockAuthenticatedUser(page);
  await mockCategories(page);

  const overview = {
    range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 },
    previous_range: { preset: "30d", start: "2026-04-02", end: "2026-04-30", days: 29 },
    current: { total_spend: "0", transaction_count: 0 },
    previous: { total_spend: "0", transaction_count: 0 },
    delta_amount: "0", delta_percent: null,
    top_categories: [], recent_transactions: [],
    budget_period: "2026-05", budgets_usage: [],
  };
  const rangeOnly = { range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 } };

  const routes: Array<[string, object]> = [
    ["/api/v1/analytics/overview**", overview],
    ["/api/v1/dashboard/summary**", overview],
    ["/api/v1/analytics/categories**", { ...rangeOnly, items: [] }],
    ["/api/v1/analytics/trends**", { ...rangeOnly, group_by: "week", points: [] }],
    ["/api/v1/analytics/merchants**", { ...rangeOnly, items: [] }],
    ["/api/v1/analytics/anomalies**", { ...rangeOnly, anomalies: [] }],
    ["/api/v1/analytics/insight-feed**", { ...rangeOnly, hero: null, source: "x", meta: {}, insights: [] }],
    ["/api/v1/transactions**", { items: [], meta: { total: 0, page: 1, size: 20 } }],
    ["/api/v1/budgets**", { items: [] }],
    ["/api/v1/insights**", { items: [], has_more: false, next_before_id: null }],
    ["/api/v1/receipts**", { items: [], meta: { total: 0, page: 1, size: 20 } }],
    ["/api/v1/chat/history**", { items: [], has_more: false, next_before_id: null }],
  ];
  for (const [path, body] of routes) {
    await page.route(`${api}${path}`, async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    });
  }
  // Registered after broad /budgets** so usage (array) wins.
  await page.route(`${api}/api/v1/budgets/usage**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
}

test.describe("Sidebar navigation", () => {
  test.beforeEach(async ({ page }) => {
    await mockEverything(page);
  });

  test("navigates to analytics screen", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Phân tích chi tiêu" }).click();
    await expect(page).toHaveURL(/\/analytics/);
    await expect(page.getByRole("heading", { name: "Phân tích chi tiết tiêu dùng" })).toBeVisible();
  });

  test("navigates to transactions list", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Danh sách giao dịch" }).click();
    await expect(page).toHaveURL(/\/transactions/);
    await expect(page.getByRole("heading", { name: "Sổ Nhật Ký Giao Dịch" })).toBeVisible();
  });

  test("navigates to budgets", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Quản lý ngân sách" }).click();
    await expect(page).toHaveURL(/\/budgets/);
    await expect(page.getByRole("heading", { name: "Quản lý ngân sách", exact: true })).toBeVisible();
  });

  test("navigates to receipts list", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Danh sách hóa đơn" }).click();
    await expect(page).toHaveURL(/\/receipts$/);
  });

  test("navigates to insights", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Thông tin Insights" }).click();
    await expect(page).toHaveURL(/\/insights/);
    await expect(page.getByRole("heading", { name: "Thông tin Insights" })).toBeVisible();
  });

  test("navigates to assistant chat", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Trợ lý tài chính (AI)" }).click();
    await expect(page).toHaveURL(/\/chat/);
    await expect(page.getByRole("heading", { name: "Trợ lý tài chính (AI)" })).toBeVisible();
  });

  test("navigates to settings", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Cài đặt hệ thống" }).click();
    await expect(page).toHaveURL(/\/settings/);
  });

  test("navigates to receipt upload", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Tải hóa đơn lên (OCR)" }).click();
    await expect(page).toHaveURL(/\/receipts\/upload/);
  });
});
