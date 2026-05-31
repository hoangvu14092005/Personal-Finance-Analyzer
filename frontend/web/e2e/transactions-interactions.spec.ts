import { expect, test, type Page } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser } from "./helpers";

function txn(id: number, merchant: string, amount: string) {
  return {
    id, user_id: 1, category_id: 1, category_name: "Ăn uống",
    receipt_upload_id: null, has_invoice: false, merchant_name: merchant,
    amount, currency: "VND", transaction_date: "2026-05-20",
    source: "manual", status: "confirmed", confirmed_at: "2026-05-20T00:00:00Z",
    note: null, created_at: "2026-05-20T00:00:00Z",
  };
}

async function mockTxnList(page: Page, opts: { empty?: boolean } = {}) {
  const api = backendBaseUrl();
  await mockAuthenticatedUser(page);
  await page.route(`${api}/api/v1/transactions**`, async (route) => {
    const req = route.request();
    if (req.method() === "DELETE") {
      await route.fulfill({ status: 204 });
      return;
    }
    const url = new URL(req.url());
    const merchant = url.searchParams.get("merchant");
    let items = opts.empty ? [] : [txn(1, "Highlands", "68000"), txn(2, "Grab", "50000")];
    if (merchant) items = items.filter((t) => t.merchant_name.toLowerCase().includes(merchant.toLowerCase()));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items, meta: { total: items.length, page: 1, size: 20 } }),
    });
  });
}

test.describe("Transactions list interactions", () => {
  test("renders rows and stats", async ({ page }) => {
    await mockTxnList(page);
    await page.goto("/transactions");
    await expect(page.getByRole("heading", { name: "Sổ Nhật Ký Giao Dịch" })).toBeVisible();
    await expect(page.getByText("Highlands")).toBeVisible();
    await expect(page.getByText("Grab")).toBeVisible();
  });

  test("apply merchant filter narrows list", async ({ page }) => {
    await mockTxnList(page);
    await page.goto("/transactions");
    await page.getByPlaceholder("VD: Highland, Grab, Coop...").fill("Highlands");
    await page.getByRole("button", { name: "Áp dụng" }).click();
    await expect(page.getByText("Highlands")).toBeVisible();
    await expect(page.getByText("Grab")).toHaveCount(0);
  });

  test("reset filter restores list", async ({ page }) => {
    await mockTxnList(page);
    await page.goto("/transactions");
    await page.getByPlaceholder("VD: Highland, Grab, Coop...").fill("Highlands");
    await page.getByRole("button", { name: "Áp dụng" }).click();
    await page.getByRole("button", { name: "Đặt lại" }).click();
    await expect(page.getByText("Grab")).toBeVisible();
  });

  test("row click expands evidence panel", async ({ page }) => {
    await mockTxnList(page);
    await page.goto("/transactions");
    await page.getByText("Highlands").click();
    await expect(page.getByText("Giao dịch này chưa liên kết hóa đơn gốc.")).toBeVisible();
  });

  test("delete button removes a transaction after confirm", async ({ page }) => {
    await mockTxnList(page);
    page.on("dialog", (dialog) => dialog.accept());
    await page.goto("/transactions");
    await page.getByRole("button", { name: "Xóa" }).first().click();
    await expect(page.getByText(/Đã xóa giao dịch/)).toBeVisible();
  });

  test("empty state shows when no transactions", async ({ page }) => {
    await mockTxnList(page, { empty: true });
    await page.goto("/transactions");
    await expect(page.getByText("Chưa có giao dịch nào khớp với bộ lọc.")).toBeVisible();
  });

  test("new transaction button navigates to manual entry", async ({ page }) => {
    await mockTxnList(page);
    await page.goto("/transactions");
    await page.getByRole("link", { name: "Thêm giao dịch mới" }).click();
    await expect(page).toHaveURL(/\/transactions\/new/);
  });
});
