import { expect, test, type Page } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser, mockCategories } from "./helpers";

const now = "2026-05-29T08:00:00Z";

async function mockAppApi(page: Page) {
  const apiBase = backendBaseUrl();
  await mockAuthenticatedUser(page);
  await mockCategories(page);

  await page.route(`${apiBase}/api/v1/analytics/overview**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 },
        previous_range: { preset: "30d", start: "2026-04-02", end: "2026-04-30", days: 29 },
        current: { total_spend: "400000", transaction_count: 3 },
        previous: { total_spend: "250000", transaction_count: 2 },
        delta_amount: "150000",
        delta_percent: 60,
        top_categories: [
          { category_id: 1, name: "Ăn uống", color: "#2c8c66", total_amount: "240000", transaction_count: 2, percentage: 60 },
        ],
        recent_transactions: [
          { id: 101, merchant_name: "Highlands Coffee", amount: "180000", currency: "VND", transaction_date: "2026-05-12", category_id: 1, category_name: "Ăn uống" },
        ],
        budget_period: "2026-05",
        budgets_usage: [
          { budget_id: 10, category_id: 1, category_name: "Ăn uống", category_color: "#2c8c66", period_month: "2026-05", budget_amount: "300000", spent_amount: "240000", remaining_amount: "60000", percent_used: 80, status: "warning" },
        ],
      }),
    });
  });

  await page.route(`${apiBase}/api/v1/analytics/categories**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 }, items: [{ category_id: 1, name: "Ăn uống", color: "#2c8c66", total_amount: "240000", transaction_count: 2, percentage: 60 }] }) });
  });
  await page.route(`${apiBase}/api/v1/analytics/trends**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 }, group_by: "week", points: [{ period_start: "2026-05-01", period_end: "2026-05-07", amount: "120000", transaction_count: 2 }, { period_start: "2026-05-08", period_end: "2026-05-14", amount: "280000", transaction_count: 5 }] }) });
  });
  await page.route(`${apiBase}/api/v1/analytics/merchants**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 }, items: [{ merchant_name: "Highlands Coffee", total_amount: "180000", transaction_count: 3, percentage: 45 }] }) });
  });
  await page.route(`${apiBase}/api/v1/analytics/anomalies**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 }, anomalies: [{ id: "a1", type: "spike", severity: "danger", title: "Chi tiêu cafe tăng mạnh", transaction_id: 101, merchant_name: "Highlands Coffee", transaction_date: "2026-05-12", amount: "180000", baseline_amount: "50000", reason: "Cao hơn baseline" }] }) });
  });
  await page.route(`${apiBase}/api/v1/analytics/insight-feed**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 }, hero: null, source: "transactions", meta: {}, insights: [insightPayload()] }) });
  });

  await page.route(`${apiBase}/api/v1/receipts**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [{ receipt_id: 321, file_name: "highlands.jpg", content_type: "image/jpeg", status: "ready", ocr_status: "succeeded", merchant_name: "Highlands Coffee", receipt_date: "2026-05-18", total_amount: "68000", currency: "VND", has_invoice: false, created_at: now, linked_transaction: { transaction_id: 789, status: "confirmed" } }],
        meta: { total: 1, page: 1, size: 20 },
      }),
    });
  });

  await page.route(`${apiBase}/api/v1/transactions?**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [{ id: 789, user_id: 1, category_id: 1, category_name: "Ăn uống", receipt_upload_id: 321, has_invoice: false, merchant_name: "Highlands Coffee", amount: "68000", currency: "VND", transaction_date: "2026-05-18", source: "ocr", status: "confirmed", confirmed_at: now, note: "Mobile test", created_at: now }],
        meta: { total: 1, page: 1, size: 20 },
      }),
    });
  });
  await page.route(`${apiBase}/api/v1/transactions`, async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: 999, user_id: 1, category_id: null, category_name: null, receipt_upload_id: null, has_invoice: false, merchant_name: "Manual Mobile", amount: "50000", currency: "VND", transaction_date: "2026-05-29", source: "manual", status: "confirmed", confirmed_at: now, note: null, created_at: now }) });
      return;
    }
    await route.fallback();
  });

  await page.route(`${apiBase}/api/v1/budgets/usage**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ budget_id: 10, category_id: 1, category_name: "Ăn uống", category_color: "#2c8c66", period_month: "2026-05", budget_amount: "300000", spent_amount: "240000", remaining_amount: "60000", percent_used: 80, status: "warning" }]) });
  });
  await page.route(`${apiBase}/api/v1/budgets**`, async (route) => {
    if (route.request().url().includes("/api/v1/budgets/usage")) {
      await route.fallback();
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [{ id: 10, user_id: 1, category_id: 1, period_month: "2026-05", amount: "300000", created_at: now, updated_at: now }] }) });
  });

  await page.route(`${apiBase}/api/v1/insights/generate`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [insightPayload()], generated_count: 1 }) });
  });
  await page.route(`${apiBase}/api/v1/insights**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [insightPayload()], has_more: false, next_before_id: null }) });
  });

  await page.route(`${apiBase}/api/v1/chat/history**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], has_more: false, next_before_id: null }) });
  });
  await page.route(`${apiBase}/api/v1/chat/message`, async (route) => {
    await route.fulfill({ status: 200, contentType: "text/event-stream", body: `event: token\ndata: {"content":"Mobile chat OK"}\n\nevent: done\ndata: {}\n\n` });
  });

  await page.route(`${apiBase}/api/v1/users/me`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: 1, email: "mobile@example.com", full_name: "Mobile Tester", currency: "VND", timezone: "Asia/Ho_Chi_Minh", locale: "vi-VN", is_active: true, created_at: now }) });
  });
  await page.route(`${apiBase}/api/v1/settings/finance`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ default_currency: "VND", timezone: "Asia/Ho_Chi_Minh", locale: "vi-VN", default_analytics_range: "30d", budget_month_start_day: 1, number_format_locale: "vi-VN", show_decimals: false, updated_at: now }) });
  });
  await page.route(`${apiBase}/api/v1/settings/ai`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ allow_ai_data_processing: true, auto_generate_insights: true, assistant_use_history: true, updated_at: now }) });
  });
  await page.route(`${apiBase}/api/v1/settings/notifications`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ email_notifications_enabled: true, push_notifications_enabled: false, budget_alerts_enabled: true, receipt_notifications_enabled: true, insight_notifications_enabled: true, updated_at: now }) });
  });
  await page.route(`${apiBase}/api/v1/settings/privacy`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ receipt_file_retention_days: 365, raw_prompt_retention_days: 30, updated_at: now }) });
  });
  await page.route(`${apiBase}/api/v1/security/sessions`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [{ id: "session-1", user_id: 1, email: "mobile@example.com", is_current: true, created_at: now }] }) });
  });
  await page.route(`${apiBase}/api/v1/security/login-history`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [] }) });
  });
  await page.route(`${apiBase}/api/v1/billing/plan`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ plan_id: "free", name: "Free", status: "active", currency: "VND", monthly_price: "0", features: [] }) });
  });
  await page.route(`${apiBase}/api/v1/billing/usage`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ transaction_count: 1, receipt_count: 1, invoice_count: 0, insight_count: 1, storage_backend: "local" }) });
  });
  await page.route(`${apiBase}/api/v1/audit-log**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [] }) });
  });
}

function insightPayload() {
  return { id: 1, type: "budget_risk", severity: "warning", title: "Ăn uống sắp vượt ngân sách", summary: "Bạn đã dùng phần lớn ngân sách ăn uống.", evidence: [{ category: "Ăn uống" }], actions: [], range_start: "2026-05-01", range_end: "2026-05-29", status: "active", dismissed_at: null, created_at: now, updated_at: now };
}

async function expectNoPageHorizontalOverflow(page: Page) {
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 2);
}

test.describe("Mobile responsive layout", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true });

  test.beforeEach(async ({ page }) => {
    await mockAppApi(page);
  });

  test("mobile drawer exposes the primary navigation", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("button", { name: "Toggle navigation" })).toBeVisible();
    await page.getByRole("button", { name: "Toggle navigation" }).click();
    await expect(page.getByRole("link", { name: "Tổng quan" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Tải hóa đơn lên (OCR)", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Cài đặt hệ thống" })).toBeVisible();
    await expectNoPageHorizontalOverflow(page);
  });

  for (const [path, heading] of [
    ["/dashboard", /^Chào mừng trở lại/],
    ["/analytics", "Phân tích chi tiết tiêu dùng"],
    ["/receipts", "Nhật ký danh sách hóa đơn tải lên"],
    ["/receipts/upload", "Tự Động Trích Xuất Hóa Đơn (OCR Scan)"],
    ["/transactions", "Sổ Nhật Ký Giao Dịch"],
    ["/transactions/new", "Ghi chép giao dịch thủ công"],
    ["/budgets", "Quản lý ngân sách"],
    ["/insights", "Thông tin Insights"],
    ["/chat", "Trợ lý tài chính (AI)"],
    ["/settings", "Cài Đặt Hệ Thống"],
  ] as const) {
    test(`${path} fits mobile viewport without page-level horizontal overflow`, async ({ page }) => {
      await page.goto(path);
      const matcher =
        typeof heading === "string"
          ? { name: heading, exact: true }
          : { name: heading };
      await expect(page.getByRole("heading", matcher)).toBeVisible();
      await expectNoPageHorizontalOverflow(page);
    });
  }
});
