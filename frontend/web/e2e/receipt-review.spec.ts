import { expect, test } from "@playwright/test";

import { backendBaseUrl, registerAndLogin } from "./helpers";

/**
 * E2E cho luồng OCR review (Phase 3.4 + 3.11).
 *
 * Để tránh phụ thuộc worker + Redis, test này mock endpoint
 * `GET /api/v1/receipts/{id}/draft` qua Playwright `page.route()`.
 * Phần còn lại (categories list, POST transaction) gọi backend thật.
 *
 * Test này verify:
 * - Trang review render với data từ /draft response.
 * - User có thể chỉnh field rồi submit.
 * - Sau submit redirect về /transactions với banner success.
 */
test.describe("Receipt review form (Phase 3.4)", () => {
  test("review form pre-fills draft and saves transaction", async ({ page }) => {
    await registerAndLogin(page);

    // Lấy receipt_id giả nào cũng được vì /draft đã mock — chọn 999.
    const fakeReceiptId = 999;
    const draftPayload = {
      receipt_id: fakeReceiptId,
      receipt_status: "ready",
      provider: "mock-ocr",
      confidence: 0.85,
      merchant_name: "Highlands Coffee",
      transaction_date: "2026-01-15",
      amount: "75000",
      currency: "VND",
      suggested_category_id: null,
      raw_text: "Highlands Coffee\n75,000 VND\n15/01/2026",
    };

    const apiBase = backendBaseUrl();
    // Mock chỉ endpoint /draft; các endpoint khác vẫn đi backend thật.
    await page.route(
      `${apiBase}/api/v1/receipts/${fakeReceiptId}/draft`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(draftPayload),
        });
      },
    );

    await page.goto(`/receipts/${fakeReceiptId}/review`);

    // Header & confidence badge.
    await expect(
      page.getByRole("heading", { name: /Review giao dịch từ OCR/i }),
    ).toBeVisible();
    await expect(page.getByText(/85%/)).toBeVisible();

    // Form pre-filled.
    await expect(page.getByLabel("Merchant")).toHaveValue("Highlands Coffee");
    await expect(page.getByLabel("Số tiền")).toHaveValue("75000");
    await expect(page.getByLabel("Tiền tệ")).toHaveValue("VND");
    await expect(page.getByLabel("Ngày giao dịch")).toHaveValue("2026-01-15");

    // Sửa note + submit.
    await page.getByLabel("Ghi chú").fill("Cà phê sáng - test E2E");
    await page.getByRole("button", { name: /Lưu giao dịch/i }).click();

    // Sau khi save → redirect /transactions?created=N.
    await expect(page).toHaveURL(/\/transactions\?created=\d+/, {
      timeout: 10_000,
    });
    await expect(page.getByText(/Đã lưu giao dịch #/)).toBeVisible();
    await expect(page.getByText("Highlands Coffee")).toBeVisible();
  });

  test("low-confidence draft shows warning banner", async ({ page }) => {
    await registerAndLogin(page);

    const fakeReceiptId = 998;
    const apiBase = backendBaseUrl();
    await page.route(
      `${apiBase}/api/v1/receipts/${fakeReceiptId}/draft`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            receipt_id: fakeReceiptId,
            receipt_status: "ready",
            provider: "mock-ocr",
            confidence: 0.45, // dưới ngưỡng 0.7.
            merchant_name: "Unclear Merchant",
            transaction_date: "2026-01-15",
            amount: "12000",
            currency: "VND",
            suggested_category_id: null,
            raw_text: null,
          }),
        });
      },
    );

    await page.goto(`/receipts/${fakeReceiptId}/review`);

    // Banner warning xuất hiện do confidence < 0.7.
    await expect(page.getByText(/OCR confidence thấp/i)).toBeVisible();
  });

  test("missing OCR draft shows fallback to manual entry", async ({ page }) => {
    await registerAndLogin(page);

    const fakeReceiptId = 997;
    const apiBase = backendBaseUrl();
    await page.route(
      `${apiBase}/api/v1/receipts/${fakeReceiptId}/draft`,
      async (route) => {
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({ detail: "OCR result not ready" }),
        });
      },
    );

    await page.goto(`/receipts/${fakeReceiptId}/review`);

    await expect(page.getByText(/Không tải được draft/i)).toBeVisible();
    await expect(
      page.getByRole("link", { name: /nhập tay/i }),
    ).toBeVisible();
  });
});
