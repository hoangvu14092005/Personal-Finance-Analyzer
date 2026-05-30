import { expect, test } from "@playwright/test";

import { backendBaseUrl } from "./helpers";

test.describe("Receipts list", () => {
  test("renders receipt retrieval filters and linked transaction state", async ({ page }) => {
    const apiBase = backendBaseUrl();
    await page.route(`${apiBase}/api/v1/auth/me`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user: {
            id: 1,
            email: "receipt-list@example.com",
            full_name: "Receipt Tester",
            currency: "VND",
            timezone: "Asia/Ho_Chi_Minh",
            locale: "vi-VN",
          },
        }),
      });
    });

    let lastReceiptsUrl = "";
    await page.route(`${apiBase}/api/v1/receipts**`, async (route) => {
      lastReceiptsUrl = route.request().url();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              receipt_id: 321,
              file_name: "highlands.jpg",
              content_type: "image/jpeg",
              status: "ready",
              ocr_status: "succeeded",
              merchant_name: "Highlands Coffee",
              receipt_date: "2026-05-18",
              total_amount: "68000.00",
              currency: "VND",
              has_invoice: true,
              created_at: "2026-05-19T03:10:00Z",
              linked_transaction: {
                transaction_id: 789,
                status: "confirmed",
              },
            },
          ],
          meta: { total: 1, page: 1, size: 20 },
        }),
      });
    });

    await page.goto("/receipts");
    await expect(page.getByRole("heading", { name: /Nhật ký danh sách hóa đơn tải lên/i })).toBeVisible();
    await expect(page.getByText("Highlands Coffee")).toBeVisible();
    await expect(page.getByText("68.000 VND")).toBeVisible();
    await expect(page.getByText("TX #789")).toBeVisible();
    await expect(page.getByRole("link", { name: /#321 · highlands.jpg/i })).toHaveAttribute(
      "href",
      "/receipts/321/review",
    );

    await page.getByLabel("Cửa hàng").fill("Highlands");
    await page.getByLabel("Giao dịch").selectOption("true");
    await page.getByRole("button", { name: "Áp dụng" }).click();

    await expect.poll(() => lastReceiptsUrl).toContain("merchant=Highlands");
    expect(lastReceiptsUrl).toContain("has_transaction=true");
  });
});
