import { expect, test, type Page } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser } from "./helpers";

const rangeInfo = { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 };

async function mockAnalytics(page: Page) {
  const api = backendBaseUrl();
  await mockAuthenticatedUser(page);
  await page.route(`${api}/api/v1/analytics/categories**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      range: rangeInfo,
      items: [
        { category_id: 1, name: "Ăn uống", color: "#f59e0b", total_amount: "240000", transaction_count: 4, percentage: 60 },
        { category_id: 2, name: "Di chuyển", color: "#10b981", total_amount: "160000", transaction_count: 3, percentage: 40 },
      ],
    }) });
  });
  await page.route(`${api}/api/v1/analytics/trends**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      range: rangeInfo, group_by: "week",
      points: [
        { period_start: "2026-05-01", period_end: "2026-05-07", amount: "120000", transaction_count: 2 },
        { period_start: "2026-05-08", period_end: "2026-05-14", amount: "280000", transaction_count: 5 },
      ],
    }) });
  });
  await page.route(`${api}/api/v1/analytics/merchants**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      range: rangeInfo,
      items: [{ merchant_name: "Highlands Coffee", total_amount: "180000", transaction_count: 3, percentage: 45 }],
    }) });
  });
  await page.route(`${api}/api/v1/analytics/anomalies**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      range: rangeInfo,
      anomalies: [{ id: "a1", type: "spike", severity: "danger", title: "Chi tiêu cafe tăng mạnh", transaction_id: 101, merchant_name: "Highlands Coffee", transaction_date: "2026-05-12", amount: "180000", baseline_amount: "50000", reason: "Cao hơn baseline 260%" }],
    }) });
  });
  await page.route(`${api}/api/v1/analytics/insight-feed**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      range: rangeInfo, hero: null, source: "x", meta: {},
      insights: [{ id: 1, type: "budget_risk", severity: "warning", title: "Sắp vượt ngân sách", summary: "...", evidence: [], actions: [], range_start: "2026-05-01", range_end: "2026-05-29", status: "active", dismissed_at: null, created_at: "2026-05-29T08:00:00Z", updated_at: "2026-05-29T08:00:00Z" }],
    }) });
  });
}

test.describe("Analytics interactions", () => {
  test.beforeEach(async ({ page }) => {
    await mockAnalytics(page);
  });

  test("renders charts and stats", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page.getByRole("heading", { name: "Phân tích chi tiết tiêu dùng" })).toBeVisible();
    await expect(page.getByText("Highlands Coffee").first()).toBeVisible();
    await expect(page.getByText("Chi tiêu cafe tăng mạnh")).toBeVisible();
  });

  test("switching range preset reloads data", async ({ page }) => {
    await page.goto("/analytics");
    await page.getByRole("button", { name: "7 ngày qua" }).click();
    await expect(page.getByText("Ăn uống").first()).toBeVisible();
  });

  test("refresh button reloads analytics", async ({ page }) => {
    await page.goto("/analytics");
    await page.getByRole("button", { name: "Làm mới phân tích" }).click();
    await expect(page.getByText("Ăn uống").first()).toBeVisible();
  });

  test("anomaly links to transaction detail", async ({ page }) => {
    await page.goto("/analytics");
    await page.getByText("Chi tiêu cafe tăng mạnh").click();
    await expect(page).toHaveURL(/\/transactions\/101/);
  });
});
