import { expect, test } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser } from "./helpers";

type Tx = {
  id: number;
  user_id: number;
  category_id: number | null;
  category_name: string | null;
  receipt_upload_id: number | null;
  has_invoice: boolean;
  merchant_name: string;
  amount: string;
  currency: string;
  transaction_date: string;
  source: string;
  status: string;
  confirmed_at: string;
  note: string | null;
  created_at: string;
};

function makeTx(id: number, merchantName: string, amount: string): Tx {
  return {
    id,
    user_id: 1,
    category_id: null,
    category_name: null,
    receipt_upload_id: id === 2 ? 321 : null,
    has_invoice: false,
    merchant_name: merchantName,
    amount,
    currency: "VND",
    transaction_date: "2026-05-29",
    source: id === 2 ? "ocr" : "manual",
    status: "confirmed",
    confirmed_at: "2026-05-29T08:00:00Z",
    note: null,
    created_at: "2026-05-29T08:00:00Z",
  };
}

test.describe("Transactions history", () => {
  test("user filters by merchant and deletes a transaction", async ({ page }) => {
    await mockAuthenticatedUser(page);
    const apiBase = backendBaseUrl();
    const merchantA = `Cafe-A-${Date.now()}`;
    const merchantB = `Diner-B-${Date.now()}`;
    let transactions = [makeTx(1, merchantA, "12000"), makeTx(2, merchantB, "55000")];

    await page.route(`${apiBase}/api/v1/transactions?**`, async (route) => {
      const url = new URL(route.request().url());
      const merchant = url.searchParams.get("merchant")?.toLowerCase() ?? "";
      const items = merchant
        ? transactions.filter((tx) => tx.merchant_name.toLowerCase().includes(merchant))
        : transactions;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items, meta: { total: items.length, page: 1, size: 20 } }),
      });
    });
    await page.route(`${apiBase}/api/v1/transactions/*`, async (route) => {
      if (route.request().method() === "DELETE") {
        const id = Number(route.request().url().split("/").pop());
        transactions = transactions.filter((tx) => tx.id !== id);
        await route.fulfill({ status: 204 });
        return;
      }
      await route.fallback();
    });

    await page.goto("/transactions");
    await expect(page.getByText(merchantA)).toBeVisible();
    await expect(page.getByText(merchantB)).toBeVisible();

    await page.getByLabel(/Tìm theo cửa hàng/i).fill(merchantA);
    await page.getByRole("button", { name: /Áp dụng/i }).click();
    await expect(page.getByText(merchantA)).toBeVisible();
    await expect(page.getByText(merchantB)).not.toBeVisible();

    await page.getByRole("button", { name: /Đặt lại/i }).click();
    await expect(page.getByText(merchantB)).toBeVisible();

    page.once("dialog", async (dialog) => {
      await dialog.accept();
    });
    const rowB = page.getByRole("row", { name: new RegExp(merchantB) });
    await rowB.getByRole("button", { name: /Xóa/i }).click();

    await expect(page.getByText(/Đã xóa giao dịch #2/)).toBeVisible();
    await expect(page.getByText(merchantB)).not.toBeVisible();
    await expect(page.getByText(merchantA)).toBeVisible();
  });
});
