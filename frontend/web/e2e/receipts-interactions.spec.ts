import { expect, test, type Page } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser } from "./helpers";

function receipt(id: number, merchant: string, opts: { linked?: boolean } = {}) {
  return {
    receipt_id: id, file_name: `r${id}.jpg`, content_type: "image/jpeg",
    status: "ready", ocr_status: "succeeded", merchant_name: merchant,
    receipt_date: "2026-05-20", total_amount: "120000", currency: "VND",
    has_invoice: true, created_at: "2026-05-20T09:00:00Z",
    linked_transaction: opts.linked ? { transaction_id: 50, status: "confirmed" } : null,
  };
}

async function mockReceipts(page: Page, opts: { empty?: boolean } = {}) {
  const api = backendBaseUrl();
  await mockAuthenticatedUser(page);
  await page.route(`${api}/api/v1/receipts**`, async (route) => {
    const url = new URL(route.request().url());
    const merchant = url.searchParams.get("merchant");
    let items = opts.empty ? [] : [receipt(1, "Highlands", { linked: true }), receipt(2, "Grab")];
    if (merchant) items = items.filter((r) => r.merchant_name.toLowerCase().includes(merchant.toLowerCase()));
    await route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ items, meta: { total: items.length, page: 1, size: 20 } }),
    });
  });
}

test.describe("Receipts list interactions", () => {
  test("renders receipts with status badges", async ({ page }) => {
    await mockReceipts(page);
    await page.goto("/receipts");
    await expect(page.getByRole("heading", { name: "Nhật ký danh sách hóa đơn tải lên" })).toBeVisible();
    await expect(page.getByText("Highlands")).toBeVisible();
    await expect(page.getByText("TX #50")).toBeVisible();
  });

  test("filter by merchant narrows the list", async ({ page }) => {
    await mockReceipts(page);
    await page.goto("/receipts");
    await page.getByPlaceholder("VD: Highlands, Grab, Coop...").fill("Grab");
    await page.getByRole("button", { name: "Áp dụng" }).click();
    await expect(page.getByText("Grab")).toBeVisible();
    await expect(page.getByText("Highlands")).toHaveCount(0);
  });

  test("reset filter restores list", async ({ page }) => {
    await mockReceipts(page);
    await page.goto("/receipts");
    await page.getByPlaceholder("VD: Highlands, Grab, Coop...").fill("Grab");
    await page.getByRole("button", { name: "Áp dụng" }).click();
    await page.getByRole("button", { name: "Đặt lại" }).click();
    await expect(page.getByText("Highlands")).toBeVisible();
  });

  test("empty state shown when no receipts", async ({ page }) => {
    await mockReceipts(page, { empty: true });
    await page.goto("/receipts");
    await expect(page.getByText("Không có hóa đơn nào khớp bộ lọc.")).toBeVisible();
  });

  test("upload button navigates to upload screen", async ({ page }) => {
    await mockReceipts(page);
    await page.goto("/receipts");
    await page.getByRole("link", { name: "Tải hóa đơn lên" }).click();
    await expect(page).toHaveURL(/\/receipts\/upload/);
  });
});
