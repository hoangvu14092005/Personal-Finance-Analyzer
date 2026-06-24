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
  // Endpoints mới (Đợt 1 BI expansion) — mock để Promise.all không reject.
  await page.route(`${api}/api/v1/analytics/products**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      range: rangeInfo,
      items: [{ item_name: "Cà phê sữa đá", total_amount: "90000", total_quantity: "2", line_count: 2, percentage: 50 }],
    }) });
  });
  await page.route(`${api}/api/v1/analytics/tax**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      range: rangeInfo, subtotal_before_tax: "100000", total_tax: "10000", grand_total: "110000",
      invoice_count: 1, effective_tax_rate: 10,
      top_sellers: [{ seller_name: "WinMart", seller_tax_id: "012345", total_amount: "110000", invoice_count: 1, percentage: 100 }],
    }) });
  });
  await page.route(`${api}/api/v1/analytics/diagnostics**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      range: rangeInfo, previous_range: rangeInfo, current_total: "400000", previous_total: "300000",
      delta_amount: "100000", delta_percent: 33.3,
      drivers: [{ category_id: 1, category_name: "Ăn uống", current_amount: "240000", previous_amount: "180000", delta_amount: "60000", delta_percent: 33.3, direction: "increase", top_merchants: [{ merchant_name: "Highlands Coffee", current_amount: "120000", previous_amount: "60000", delta_amount: "60000" }] }],
    }) });
  });
  await page.route(`${api}/api/v1/analytics/forecast**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      month: { period_month: "2026-05", days_elapsed: 29, days_in_month: 31, spent_so_far: "400000", daily_run_rate: "13793", projected_total: "427000" },
      budgets: [{ category_id: 1, category_name: "Ăn uống", budget_amount: "500000", spent_so_far: "240000", projected_spend: "256000", projected_percent: 51, status: "on_track", projected_exceed_date: null }],
    }) });
  });
  await page.route(`${api}/api/v1/analytics/calendar**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      range: rangeInfo,
      days: [{ date: "2026-05-12", amount: "180000", transaction_count: 2, intensity: 3, top_category_name: "Ăn uống", is_unusual: false }],
      legend: { levels: { "0": "no_spend", "1": "low", "2": "medium", "3": "high", "4": "unusual" } },
    }) });
  });
  await page.route(`${api}/api/v1/analytics/recurring**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      lookback_months: 6, fixed_monthly_estimate: "200000", variable_last_month: "200000",
      recurring_items: [{ merchant_name: "Netflix", months_active: 6, avg_monthly_amount: "200000", last_amount: "200000", last_date: "2026-05-01" }],
    }) });
  });
}

test.describe("Analytics interactions", () => {
  test.beforeEach(async ({ page }) => {
    await mockAnalytics(page);
  });

  test("renders charts and stats", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page.getByRole("heading", { name: "Phân tích chi tiêu" })).toBeVisible();
    // Overview tab mặc định: cảnh báo (anomaly) hiển thị.
    await expect(page.getByText("Chi tiêu cafe tăng mạnh")).toBeVisible();
    // Insight summary banner ngôn ngữ tự nhiên.
    await expect(page.getByText(/là nhóm chi lớn nhất/)).toBeVisible();
  });

  test("switching month reloads data", async ({ page }) => {
    await page.goto("/analytics");
    await page.getByLabel("Chọn tháng").selectOption({ index: 1 });
    await expect(page.getByText("Chi tiêu cafe tăng mạnh")).toBeVisible();
  });

  test("switching to Danh mục tab shows categories and merchants", async ({ page }) => {
    await page.goto("/analytics");
    await page.getByRole("button", { name: "Danh mục" }).click();
    await expect(page.getByText("Ăn uống").first()).toBeVisible();
    await expect(page.getByText("Highlands Coffee").first()).toBeVisible();
  });

  test("refresh button reloads analytics", async ({ page }) => {
    await page.goto("/analytics");
    await page.getByRole("button", { name: "Làm mới phân tích" }).click();
    await expect(page.getByText("Chi tiêu cafe tăng mạnh")).toBeVisible();
  });

  test("anomaly links to transaction detail", async ({ page }) => {
    await page.goto("/analytics");
    await page.getByText("Chi tiêu cafe tăng mạnh").click();
    await expect(page).toHaveURL(/\/transactions\/101/);
  });

  test("selecting a specific month uses a custom date range", async ({ page }) => {
    let customUrl = "";
    await page.route(`${backendBaseUrl()}/api/v1/analytics/categories**`, async (route) => {
      const url = route.request().url();
      if (url.includes("range=custom")) customUrl = url;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ range: rangeInfo, items: [] }) });
    });
    await page.goto("/analytics");
    await page.getByLabel("Chọn tháng").selectOption({ index: 1 });
    await expect.poll(() => customUrl).toContain("range=custom");
    expect(customUrl).toContain("start_date=");
    expect(customUrl).toContain("end_date=");
  });

  test("one failing endpoint shows per-section retry, not a blank page", async ({ page }) => {
    // Ghi đè trends để trả lỗi 500 — các section khác vẫn phải hiển thị.
    await page.route(`${backendBaseUrl()}/api/v1/analytics/trends**`, async (route) => {
      await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "boom" }) });
    });
    await page.goto("/analytics");
    // KPI + banner vẫn render (trang không trắng).
    await expect(page.getByRole("heading", { name: "Phân tích chi tiêu" })).toBeVisible();
    // Section trends hỏng hiện nút Thử lại.
    await expect(page.getByText("Không tải được phần này").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Thử lại" }).first()).toBeVisible();
    // Section khác (cảnh báo) vẫn render.
    await expect(page.getByText("Chi tiêu cafe tăng mạnh")).toBeVisible();
  });
});
