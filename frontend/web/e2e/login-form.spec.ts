import { expect, test } from "@playwright/test";

import { backendBaseUrl } from "./helpers";

/**
 * Login screen — form validation, error handling, navigation, success.
 * API mocked (no live backend needed).
 */
test.describe("Login form", () => {
  test("renders heading, inputs, and submit button", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Đăng nhập" })).toBeVisible();
    await expect(page.getByLabel("Mat khau")).toBeVisible();
    await expect(page.getByRole("button", { name: "Dang nhap" })).toBeVisible();
  });

  test("required fields block empty submit (HTML validation)", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Dang nhap" }).click();
    // Still on login because required inputs are empty.
    await expect(page).toHaveURL(/\/login/);
  });

  test("shows error banner on invalid credentials", async ({ page }) => {
    const apiBase = backendBaseUrl();
    await page.route(`${apiBase}/api/v1/auth/login`, async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Invalid email or password" }),
      });
    });
    await page.goto("/login");
    await page.getByPlaceholder("admin").fill("admin");
    await page.getByLabel("Mat khau").fill("wrong");
    await page.getByRole("button", { name: "Dang nhap" }).click();
    await expect(page.getByText("Invalid email or password")).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });

  test("successful login redirects to dashboard", async ({ page }) => {
    const apiBase = backendBaseUrl();
    const userBody = JSON.stringify({
      user: { id: 1, email: "admin@example.com", full_name: "Admin", currency: "VND", timezone: "Asia/Ho_Chi_Minh", locale: "vi-VN" },
    });
    await page.route(`${apiBase}/api/v1/auth/login`, async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: userBody });
    });
    await page.route(`${apiBase}/api/v1/auth/me`, async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: userBody });
    });
    await page.route(`${apiBase}/api/v1/analytics/overview**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 },
          previous_range: { preset: "30d", start: "2026-04-02", end: "2026-04-30", days: 29 },
          current: { total_spend: "0", transaction_count: 0 },
          previous: { total_spend: "0", transaction_count: 0 },
          delta_amount: "0", delta_percent: null,
          top_categories: [], recent_transactions: [],
          budget_period: "2026-05", budgets_usage: [],
        }),
      });
    });
    await page.goto("/login");
    await page.getByPlaceholder("admin").fill("admin");
    await page.getByLabel("Mat khau").fill("1");
    await page.getByRole("button", { name: "Dang nhap" }).click();
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("link to register navigates to /register", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("link", { name: "Đăng ký" }).click();
    await expect(page).toHaveURL(/\/register/);
  });
});
