import { expect, test } from "@playwright/test";

import { registerAndLogin } from "./helpers";

test.describe("Dashboard analytics (Phase 4.5+4.6+4.7)", () => {
  test("user lands on dashboard, sees empty state, can switch range", async ({
    page,
  }) => {
    await registerAndLogin(page);

    // registerAndLogin đã land /dashboard. Default range = 30d.
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeVisible();

    // User mới → empty state hiển thị (không có transaction).
    await expect(
      page.getByRole("heading", { name: /Chưa có giao dịch trong kỳ này/ }),
    ).toBeVisible();

    // Switch sang 7d và verify URL sync.
    await page.getByRole("button", { name: "7 ngày qua" }).click();
    await expect(page).toHaveURL(/range=7d/);

    // Switch sang custom → form date inputs xuất hiện.
    await page.getByRole("button", { name: "Tùy chỉnh" }).click();
    await expect(page).toHaveURL(/range=custom/);
    await expect(page.getByLabel("Từ ngày")).toBeVisible();
    await expect(page.getByLabel("Đến ngày")).toBeVisible();
  });

  test("dashboard renders summary cards and chart after creating a transaction", async ({
    page,
  }) => {
    await registerAndLogin(page);

    // Tạo 1 transaction qua manual entry để dashboard có data.
    await page.goto("/transactions/new");
    await page.getByLabel("Số tiền").fill("125000");
    await page.getByLabel("Merchant").fill("E2E Dashboard Cafe");
    await page.getByRole("button", { name: /Lưu giao dịch/i }).click();
    await expect(page).toHaveURL(/\/transactions\?created=\d+/, {
      timeout: 10_000,
    });

    // Quay lại dashboard và verify cards xuất hiện.
    await page.goto("/dashboard?range=30d");
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeVisible();

    // Summary cards: Tổng chi tiêu hiển thị 125,000.
    await expect(page.getByText("Tổng chi tiêu")).toBeVisible();
    await expect(page.getByText(/125\.000/)).toBeVisible();

    // Section chart và recent transactions render.
    await expect(
      page.getByRole("heading", { name: "Phân bổ theo danh mục" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Giao dịch gần đây" }),
    ).toBeVisible();
    await expect(page.getByText("E2E Dashboard Cafe")).toBeVisible();

    // Block so sánh kỳ trước có hiển thị.
    await expect(
      page.getByRole("heading", { name: "So sánh kỳ trước" }),
    ).toBeVisible();
  });
});
