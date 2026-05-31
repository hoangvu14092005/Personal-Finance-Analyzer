import { expect, test } from "@playwright/test";

import { backendBaseUrl } from "./helpers";

/**
 * Register screen — fields, validation, error, success redirect, navigation.
 */
test.describe("Register form", () => {
  test("renders heading, fields, and submit", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByRole("heading", { name: "Tạo tài khoản" })).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Ho va ten")).toBeVisible();
    await expect(page.getByLabel("Mat khau")).toBeVisible();
    await expect(page.getByRole("button", { name: "Tao tai khoan" })).toBeVisible();
  });

  test("shows error banner when email already registered", async ({ page }) => {
    const apiBase = backendBaseUrl();
    await page.route(`${apiBase}/api/v1/auth/register`, async (route) => {
      await route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Email already registered" }),
      });
    });
    await page.goto("/register");
    await page.getByLabel("Email").fill("dup@example.com");
    await page.getByLabel("Mat khau").fill("Test1234abc");
    await page.getByRole("button", { name: "Tao tai khoan" }).click();
    await expect(page.getByText("Email already registered")).toBeVisible();
  });

  test("successful register redirects to login", async ({ page }) => {
    const apiBase = backendBaseUrl();
    await page.route(`${apiBase}/api/v1/auth/register`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user: { id: 2, email: "fresh@example.com", full_name: null, currency: "VND", timezone: "Asia/Ho_Chi_Minh", locale: "vi-VN" },
        }),
      });
    });
    await page.goto("/register");
    await page.getByLabel("Email").fill("fresh@example.com");
    await page.getByLabel("Mat khau").fill("Test1234abc");
    await page.getByRole("button", { name: "Tao tai khoan" }).click();
    await expect(page).toHaveURL(/\/login/);
  });

  test("link to login navigates to /login", async ({ page }) => {
    await page.goto("/register");
    await page.getByRole("link", { name: "Đăng nhập" }).click();
    await expect(page).toHaveURL(/\/login/);
  });
});
