import { expect, test } from "@playwright/test";

import { registerAndLogin } from "./helpers";

test.describe("Manual transaction entry (Phase 3.6)", () => {
  test("user creates manual transaction and sees it in history", async ({ page }) => {
    await registerAndLogin(page);

    // Đến trang manual entry.
    await page.getByRole("link", { name: "New Entry" }).click();
    await expect(page).toHaveURL(/\/transactions\/new$/);
    await expect(
      page.getByRole("heading", { name: /Nhập giao dịch thủ công/i }),
    ).toBeVisible();

    // Điền form.
    const merchantName = `E2E Cafe ${Date.now()}`;
    await page.getByLabel("Merchant").fill(merchantName);
    await page.getByLabel("Số tiền").fill("87500");
    // Currency mặc định là VND.
    // Date mặc định là hôm nay (defaultDate()).
    await page.getByLabel("Ghi chú").fill("Tạo từ Playwright E2E");

    await page.getByRole("button", { name: /Lưu giao dịch/i }).click();

    // Sau khi lưu thành công redirect về /transactions?created=N.
    await expect(page).toHaveURL(/\/transactions\?created=\d+/, {
      timeout: 10_000,
    });

    // Banner success xuất hiện.
    await expect(page.getByText(/Đã lưu giao dịch #/)).toBeVisible();

    // Row mới trong table chứa merchant name vừa nhập.
    await expect(page.getByText(merchantName)).toBeVisible();
  });

  test("manual entry rejects empty amount", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/transactions/new");

    // Cố gắng submit không có amount: required attr sẽ chặn submit ở browser
    // level → chỉ verify URL không đổi (không redirect /transactions).
    await page.getByLabel("Merchant").fill("X");
    await page.getByRole("button", { name: /Lưu giao dịch/i }).click();
    await page.waitForTimeout(500);
    await expect(page).toHaveURL(/\/transactions\/new$/);
  });
});
