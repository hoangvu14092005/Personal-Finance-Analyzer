import { expect, test } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser, mockCategories } from "./helpers";

test.describe("Manual transaction entry", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page);
    await mockCategories(page);
  });

  test("user creates manual transaction and sees it in history", async ({ page }) => {
    const apiBase = backendBaseUrl();
    const merchantName = `E2E Cafe ${Date.now()}`;
    let createdTransaction = {
      id: 8842,
      user_id: 1,
      category_id: null,
      category_name: null,
      receipt_upload_id: null,
      has_invoice: false,
      merchant_name: merchantName,
      amount: "87500",
      currency: "VND",
      transaction_date: "2026-05-29",
      source: "manual",
      status: "confirmed",
      confirmed_at: "2026-05-29T08:00:00Z",
      note: "Tạo từ Playwright E2E",
      created_at: "2026-05-29T08:00:00Z",
    };

    await page.route(`${apiBase}/api/v1/transactions`, async (route) => {
      if (route.request().method() === "POST") {
        const body = await route.request().postDataJSON();
        createdTransaction = {
          ...createdTransaction,
          merchant_name: body.merchant_name,
          amount: body.amount,
          currency: body.currency,
          transaction_date: body.transaction_date,
          note: body.note,
        };
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(createdTransaction) });
        return;
      }
      await route.fallback();
    });
    await page.route(`${apiBase}/api/v1/transactions?**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [createdTransaction], meta: { total: 1, page: 1, size: 20 } }),
      });
    });

    await page.goto("/transactions/new");
    await expect(page.getByRole("heading", { name: /Ghi chép giao dịch thủ công/i })).toBeVisible();

    await page.getByLabel("Cửa hàng / mô tả giao dịch").fill(merchantName);
    await page.getByLabel("Số tiền").fill("87500");
    await page.getByLabel("Ghi chú").fill("Tạo từ Playwright E2E");
    await page.getByRole("button", { name: /Lưu giao dịch/i }).click();

    await expect(page).toHaveURL(/\/transactions\?created=8842/);
    await expect(page.getByText(/Đã lưu giao dịch #8842/)).toBeVisible();
    await expect(page.getByText(merchantName)).toBeVisible();
    await expect(page.getByText("manual")).toBeVisible();
  });

  test("manual entry rejects empty amount", async ({ page }) => {
    await page.goto("/transactions/new");
    await page.getByLabel("Cửa hàng / mô tả giao dịch").fill("X");
    await page.getByRole("button", { name: /Lưu giao dịch/i }).click();
    await page.waitForTimeout(300);
    await expect(page).toHaveURL(/\/transactions\/new$/);
  });
});
