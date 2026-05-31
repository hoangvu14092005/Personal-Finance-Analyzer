import { expect, test } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser } from "./helpers";

test.describe("Auth flow", () => {
  test("user can register, login, and reach the dashboard shell", async ({ page }) => {
    const apiBase = backendBaseUrl();

    await page.route(`${apiBase}/api/v1/auth/register`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user: {
            id: 1,
            email: "new-user@example.com",
            full_name: "E2E Smoke",
            currency: "VND",
            timezone: "Asia/Ho_Chi_Minh",
            locale: "vi-VN",
          },
        }),
      });
    });
    await page.route(`${apiBase}/api/v1/auth/login`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user: {
            id: 1,
            email: "new-user@example.com",
            full_name: "E2E Smoke",
            currency: "VND",
            timezone: "Asia/Ho_Chi_Minh",
            locale: "vi-VN",
          },
        }),
      });
    });
    await mockAuthenticatedUser(page);
    await page.route(`${apiBase}/api/v1/analytics/overview**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 },
          previous_range: { preset: "30d", start: "2026-04-02", end: "2026-04-30", days: 29 },
          current: { total_spend: "0", transaction_count: 0 },
          previous: { total_spend: "0", transaction_count: 0 },
          delta_amount: "0",
          delta_percent: null,
          top_categories: [],
          recent_transactions: [],
          budget_period: "2026-05",
          budgets_usage: [],
        }),
      });
    });

    await page.goto("/register");
    await page.getByLabel("Email").fill("new-user@example.com");
    await page.getByLabel("Ho va ten").fill("E2E Smoke");
    await page.getByLabel("Mat khau").fill("Test1234abc");
    await page.getByRole("button", { name: "Tao tai khoan" }).click();
    await expect(page).toHaveURL(/\/login/);

    await page.getByLabel("Email").fill("new-user@example.com");
    await page.getByLabel("Mat khau").fill("Test1234abc");
    await page.getByRole("button", { name: "Dang nhap" }).click();

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole("link", { name: "Tổng quan" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Tải hóa đơn lên (OCR)" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Danh sách giao dịch" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /^Chào mừng trở lại/ })).toBeVisible();
  });
});
