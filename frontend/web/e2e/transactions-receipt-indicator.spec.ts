import { expect, test } from "@playwright/test";

import { backendBaseUrl } from "./helpers";

test.describe("Transaction receipt indicator", () => {
  test("opens receipt evidence from a transaction row", async ({ page }) => {
    const apiBase = backendBaseUrl();
    await page.route(`${apiBase}/api/v1/auth/me`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user: {
            id: 1,
            email: "tx-receipt@example.com",
            full_name: "TX Receipt Tester",
            currency: "VND",
            timezone: "Asia/Ho_Chi_Minh",
            locale: "vi-VN",
          },
        }),
      });
    });

    await page.route(`${apiBase}/api/v1/transactions?**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              id: 789,
              user_id: 1,
              category_id: null,
              category_name: null,
              receipt_upload_id: 321,
              has_invoice: false,
              merchant_name: "Highlands Coffee",
              amount: "68000.00",
              currency: "VND",
              transaction_date: "2026-05-18",
              source: "ocr",
              status: "confirmed",
              confirmed_at: "2026-05-19T03:11:00Z",
              note: "Morning coffee",
              created_at: "2026-05-19T03:11:00Z",
            },
          ],
          meta: { total: 1, page: 1, size: 20 },
        }),
      });
    });

    await page.route(`${apiBase}/api/v1/transactions/789/receipt`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          receipt_id: 321,
          file_name: "highlands.jpg",
          content_type: "image/jpeg",
          status: "ready",
          ocr_status: "succeeded",
          merchant_name: "Highlands Coffee",
          receipt_date: "2026-05-18",
          total_amount: "68000.00",
          currency: "VND",
          has_invoice: false,
          created_at: "2026-05-19T03:10:00Z",
          linked_transaction: {
            transaction_id: 789,
            status: "confirmed",
          },
        }),
      });
    });

    await page.goto("/transactions");
    await expect(page.getByText("Highlands Coffee")).toBeVisible();
    await expect(page.getByLabel("Có chứng từ")).toBeVisible();
    const txRow = page.getByRole("row", { name: /Highlands Coffee/i });
    await expect(txRow.getByRole("link", { name: "Hóa đơn" })).toHaveAttribute(
      "href",
      "/receipts/321/review",
    );

    await txRow.click();
    await expect(page.getByText("Chứng từ gốc")).toBeVisible();
    await expect(page.getByText("#321 · highlands.jpg · image/jpeg")).toBeVisible();
    await expect(page.getByText(/Tổng OCR:\s*68\.000 VND/)).toBeVisible();
  });
});
