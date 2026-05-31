import { expect, test, type Page } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser } from "./helpers";

/**
 * Receipt upload — multi-file selection + per-file progress.
 * Mocks upload (returns ready immediately) so no worker needed.
 */
async function mockUploadReady(page: Page) {
  const api = backendBaseUrl();
  await mockAuthenticatedUser(page);
  let nextId = 100;
  await page.route(`${api}/api/v1/receipts**`, async (route) => {
    const req = route.request();
    if (req.method() === "POST") {
      const id = nextId++;
      await route.fulfill({
        status: 201, contentType: "application/json",
        body: JSON.stringify({ receipt_id: id, status: "ready" }),
      });
      return;
    }
    await route.fallback();
  });
}

async function attachFiles(page: Page, names: string[]) {
  await page.setInputFiles('input[type="file"]', names.map((name) => ({
    name, mimeType: "image/png",
    buffer: Buffer.from([0x89, 0x50, 0x4e, 0x47]),
  })));
}

test.describe("Receipt multi-upload", () => {
  test("page shows multi-file hint", async ({ page }) => {
    await mockUploadReady(page);
    await page.goto("/receipts/upload");
    await expect(page.getByText("Kéo thả nhiều hóa đơn", { exact: false })).toBeVisible();
    await expect(page.getByText(/Tối đa 10 hóa đơn/)).toBeVisible();
  });

  test("selecting multiple files lists them all", async ({ page }) => {
    await mockUploadReady(page);
    await page.goto("/receipts/upload");
    await attachFiles(page, ["a.png", "b.png", "c.png"]);
    await expect(page.getByText("a.png")).toBeVisible();
    await expect(page.getByText("b.png")).toBeVisible();
    await expect(page.getByText("c.png")).toBeVisible();
    await expect(page.getByRole("button", { name: /Tải lên và quét OCR \(3\)/ })).toBeVisible();
  });

  test("remove a queued file before upload", async ({ page }) => {
    await mockUploadReady(page);
    await page.goto("/receipts/upload");
    await attachFiles(page, ["a.png", "b.png"]);
    await page.getByRole("button", { name: "Bỏ" }).first().click();
    await expect(page.getByRole("button", { name: /Tải lên và quét OCR \(1\)/ })).toBeVisible();
  });

  test("upload multiple files marks each ready and shows list link", async ({ page }) => {
    await mockUploadReady(page);
    await page.goto("/receipts/upload");
    await attachFiles(page, ["a.png", "b.png"]);
    await page.getByRole("button", { name: /Tải lên và quét OCR/ }).click();
    // Both reach ready state → "Kiểm tra" buttons appear.
    await expect(page.getByRole("link", { name: "Kiểm tra" })).toHaveCount(2);
    await expect(page.getByRole("link", { name: "Xem danh sách hóa đơn" })).toBeVisible();
  });
});
