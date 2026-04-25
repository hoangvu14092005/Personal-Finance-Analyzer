import { expect, test } from "@playwright/test";

import { registerAndLogin } from "./helpers";

/**
 * E2E cho transaction history page (Phase 3.10) — verify list, filter, delete
 * sau khi user có 2 transaction tạo từ manual entry.
 */
test.describe("Transactions history (Phase 3.10)", () => {
  test("user filters by merchant and deletes a transaction", async ({ page }) => {
    await registerAndLogin(page);

    // Tạo 2 manual transaction với merchant khác nhau.
    const merchantA = `Cafe-A-${Date.now()}`;
    const merchantB = `Diner-B-${Date.now()}`;

    for (const [merchant, amount] of [
      [merchantA, "12000"],
      [merchantB, "55000"],
    ]) {
      await page.goto("/transactions/new");
      await page.getByLabel("Merchant").fill(merchant);
      await page.getByLabel("Số tiền").fill(amount);
      await page.getByRole("button", { name: /Lưu giao dịch/i }).click();
      await expect(page).toHaveURL(/\/transactions\?created=\d+/, {
        timeout: 10_000,
      });
    }

    // Cả 2 merchant đều xuất hiện.
    await page.goto("/transactions");
    await expect(page.getByText(merchantA)).toBeVisible();
    await expect(page.getByText(merchantB)).toBeVisible();

    // Filter theo merchant A.
    await page.getByLabel(/Tìm theo merchant/i).fill(merchantA);
    await page.getByRole("button", { name: /Áp dụng/i }).click();
    await expect(page.getByText(merchantA)).toBeVisible();
    await expect(page.getByText(merchantB)).not.toBeVisible();

    // Reset filter.
    await page.getByRole("button", { name: /Đặt lại/i }).click();
    await expect(page.getByText(merchantB)).toBeVisible();

    // Delete merchant B's transaction.
    page.once("dialog", async (dialog) => {
      await dialog.accept();
    });
    const rowB = page.getByRole("row", { name: new RegExp(merchantB) });
    await rowB.getByRole("button", { name: /Xóa/i }).click();

    // Sau delete: row B không còn, banner success xuất hiện.
    await expect(page.getByText(/Đã xóa giao dịch #/)).toBeVisible();
    await expect(page.getByText(merchantB)).not.toBeVisible();
    // Merchant A vẫn còn.
    await expect(page.getByText(merchantA)).toBeVisible();
  });
});
