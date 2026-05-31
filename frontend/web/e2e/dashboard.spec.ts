import { expect, test } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser } from "./helpers";

function overviewPayload(transactionCount = 2) {
  return {
    range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 },
    previous_range: { preset: "30d", start: "2026-04-02", end: "2026-04-30", days: 29 },
    current: { total_spend: transactionCount > 0 ? "400000" : "0", transaction_count: transactionCount },
    previous: { total_spend: "250000", transaction_count: 2 },
    delta_amount: transactionCount > 0 ? "150000" : "0",
    delta_percent: transactionCount > 0 ? 60 : null,
    top_categories: transactionCount > 0
      ? [
          { category_id: 1, name: "Ăn uống", color: "#2c8c66", total_amount: "240000", transaction_count: 4, percentage: 60 },
          { category_id: 2, name: "Di chuyển", color: "#2c84e0", total_amount: "160000", transaction_count: 3, percentage: 40 },
        ]
      : [],
    recent_transactions: transactionCount > 0
      ? [
          { id: 101, merchant_name: "Highlands Coffee", amount: "180000", currency: "VND", transaction_date: "2026-05-12", category_id: 1, category_name: "Ăn uống" },
        ]
      : [],
    budget_period: "2026-05",
    budgets_usage: transactionCount > 0
      ? [
          { budget_id: 10, category_id: 1, category_name: "Ăn uống", category_color: "#2c8c66", period_month: "2026-05", budget_amount: "300000", spent_amount: "240000", remaining_amount: "60000", percent_used: 80, status: "warning" },
        ]
      : [],
  };
}

test.describe("Dashboard command center", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page);
  });

  test("renders confirmed transaction overview and range controls", async ({ page }) => {
    const apiBase = backendBaseUrl();
    let lastOverviewUrl = "";
    await page.route(`${apiBase}/api/v1/analytics/overview**`, async (route) => {
      lastOverviewUrl = route.request().url();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(overviewPayload()),
      });
    });

    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: /^Chào mừng trở lại/ })).toBeVisible();
    await expect(page.getByText("400.000 VND")).toBeVisible();
    await expect(page.getByText("Highlands Coffee")).toBeVisible();
    await expect(page.getByText("Hóa đơn OCR cần được xác nhận thành giao dịch trước khi cộng vào báo cáo và ngân sách.")).toBeVisible();

    await page.getByRole("button", { name: "7 ngày qua" }).click();
    await expect(page).toHaveURL(/range=7d/);
    await expect.poll(() => lastOverviewUrl).toContain("range=7d");

    await page.getByRole("button", { name: "Tùy chỉnh" }).click();
    await expect(page.getByLabel("Từ ngày")).toBeVisible();
    await expect(page.getByLabel("Đến ngày")).toBeVisible();
  });

  test("renders empty state when there are no confirmed transactions", async ({ page }) => {
    const apiBase = backendBaseUrl();
    await page.route(`${apiBase}/api/v1/analytics/overview**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(overviewPayload(0)),
      });
    });

    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Chưa có dữ liệu để phân tích" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Tải hóa đơn lên" }).first()).toBeVisible();
  });
});
