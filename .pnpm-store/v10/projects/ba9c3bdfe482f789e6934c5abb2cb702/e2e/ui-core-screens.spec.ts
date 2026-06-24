import { expect, test } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser, mockCategories } from "./helpers";

const now = "2026-05-29T08:00:00Z";

async function mockAnalytics(page: import("@playwright/test").Page) {
  const apiBase = backendBaseUrl();
  await page.route(`${apiBase}/api/v1/analytics/categories**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 },
        items: [
          { category_id: 1, name: "Ăn uống", total_amount: "240000", transaction_count: 4, percentage: 60 },
          { category_id: 2, name: "Di chuyển", total_amount: "160000", transaction_count: 3, percentage: 40 },
        ],
      }),
    });
  });
  await page.route(`${apiBase}/api/v1/analytics/trends**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 },
        group_by: "week",
        points: [
          { period_start: "2026-05-01", period_end: "2026-05-07", amount: "120000", transaction_count: 2 },
          { period_start: "2026-05-08", period_end: "2026-05-14", amount: "280000", transaction_count: 5 },
        ],
      }),
    });
  });
  await page.route(`${apiBase}/api/v1/analytics/merchants**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 },
        items: [
          { merchant_name: "Highlands Coffee", total_amount: "180000", transaction_count: 3, percentage: 45 },
          { merchant_name: "Grab", total_amount: "90000", transaction_count: 2, percentage: 22.5 },
        ],
      }),
    });
  });
  await page.route(`${apiBase}/api/v1/analytics/anomalies**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 },
        anomalies: [
          {
            id: "anomaly-1",
            type: "spike",
            severity: "danger",
            title: "Chi tiêu cafe tăng mạnh",
            transaction_id: 101,
            merchant_name: "Highlands Coffee",
            transaction_date: "2026-05-12",
            amount: "180000",
            baseline_amount: "50000",
            reason: "Cao hơn baseline 260%",
          },
        ],
      }),
    });
  });
  await page.route(`${apiBase}/api/v1/analytics/insight-feed**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        range: { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 },
        hero: null,
        source: "transactions",
        meta: {},
        insights: [
          {
            id: 1,
            type: "budget_risk",
            severity: "warning",
            title: "Ăn uống sắp vượt ngân sách",
            summary: "Bạn đã dùng phần lớn ngân sách ăn uống.",
            evidence: [{ category: "Ăn uống", spent: 240000 }],
            actions: [],
            range_start: "2026-05-01",
            range_end: "2026-05-29",
            status: "active",
            dismissed_at: null,
            created_at: now,
            updated_at: now,
          },
        ],
      }),
    });
  });
  // Endpoints mới (Đợt 1) — mock để Promise.all không reject.
  const r30 = { preset: "30d", start: "2026-05-01", end: "2026-05-29", days: 29 };
  await page.route(`${apiBase}/api/v1/analytics/products**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ range: r30, items: [{ item_name: "Cà phê sữa đá", total_amount: "90000", total_quantity: "2", line_count: 2, percentage: 50 }] }) });
  });
  await page.route(`${apiBase}/api/v1/analytics/tax**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ range: r30, subtotal_before_tax: "100000", total_tax: "10000", grand_total: "110000", invoice_count: 1, effective_tax_rate: 10, top_sellers: [{ seller_name: "WinMart", seller_tax_id: "012345", total_amount: "110000", invoice_count: 1, percentage: 100 }] }) });
  });
  await page.route(`${apiBase}/api/v1/analytics/diagnostics**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ range: r30, previous_range: r30, current_total: "400000", previous_total: "300000", delta_amount: "100000", delta_percent: 33.3, drivers: [{ category_id: 1, category_name: "Ăn uống", current_amount: "240000", previous_amount: "180000", delta_amount: "60000", delta_percent: 33.3, direction: "increase", top_merchants: [] }] }) });
  });
  await page.route(`${apiBase}/api/v1/analytics/forecast**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ month: { period_month: "2026-05", days_elapsed: 29, days_in_month: 31, spent_so_far: "400000", daily_run_rate: "13793", projected_total: "427000" }, budgets: [] }) });
  });
  await page.route(`${apiBase}/api/v1/analytics/calendar**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ range: r30, days: [{ date: "2026-05-12", amount: "180000", transaction_count: 2, intensity: 3, top_category_name: "Ăn uống", is_unusual: false }], legend: { levels: {} } }) });
  });
  await page.route(`${apiBase}/api/v1/analytics/recurring**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ lookback_months: 6, fixed_monthly_estimate: "0", variable_last_month: "0", recurring_items: [] }) });
  });
}

async function mockBudgets(page: import("@playwright/test").Page) {
  const apiBase = backendBaseUrl();
  await mockCategories(page);
  await page.route(`${apiBase}/api/v1/budgets**`, async (route) => {
    if (route.request().url().includes("/api/v1/budgets/usage")) {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          { id: 10, user_id: 1, category_id: 1, period_month: "2026-05", amount: "300000", created_at: now, updated_at: now },
        ],
      }),
    });
  });
  await page.route(`${apiBase}/api/v1/budgets/usage**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          budget_id: 10,
          category_id: 1,
          category_name: "Ăn uống",
          category_color: "#2c8c66",
          period_month: "2026-05",
          budget_amount: "300000",
          spent_amount: "270000",
          remaining_amount: "30000",
          percent_used: 90,
          status: "warning",
        },
      ]),
    });
  });
}

function insightPayload() {
  return {
    id: 3,
    type: "budget_risk",
    severity: "danger",
    title: "Ăn uống vượt ngưỡng",
    summary: "Chi tiêu ăn uống đang vượt ngưỡng an toàn.",
    evidence: [{ category: "Ăn uống", percent_used: 112 }],
    actions: [],
    range_start: "2026-05-01",
    range_end: "2026-05-29",
    status: "active",
    dismissed_at: null,
    created_at: now,
    updated_at: now,
  };
}

async function mockInsights(page: import("@playwright/test").Page) {
  const apiBase = backendBaseUrl();
  await page.route(`${apiBase}/api/v1/insights**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [insightPayload()], has_more: false, next_before_id: null }),
    });
  });
  await page.route(`${apiBase}/api/v1/insights/generate`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [insightPayload()], generated_count: 1 }),
    });
  });
}

async function mockSettings(page: import("@playwright/test").Page) {
  const apiBase = backendBaseUrl();
  await page.route(`${apiBase}/api/v1/users/me`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: 1, email: "ui-test@example.com", full_name: "UI Tester", currency: "VND", timezone: "Asia/Ho_Chi_Minh", locale: "vi-VN", is_active: true, created_at: now }),
    });
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
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [{ id: "session-1", user_id: 1, email: "ui-test@example.com", is_current: true, created_at: now }] }) });
  });
  await page.route(`${apiBase}/api/v1/security/login-history`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [{ id: "login-1", occurred_at: now, event: "login", ip_address: null, user_agent: null }] }) });
  });
  await page.route(`${apiBase}/api/v1/billing/plan`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ plan_id: "free", name: "Free", status: "active", currency: "VND", monthly_price: "0", features: ["OCR", "Analytics"] }) });
  });
  await page.route(`${apiBase}/api/v1/billing/usage`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ transaction_count: 12, receipt_count: 4, invoice_count: 1, insight_count: 3, storage_backend: "local" }) });
  });
  await page.route(`${apiBase}/api/v1/audit-log**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [{ id: "audit-1", event: "settings.updated", occurred_at: now, actor_user_id: 1, target_type: "settings", target_id: "finance", metadata: {} }] }) });
  });
}

async function mockChat(page: import("@playwright/test").Page) {
  const apiBase = backendBaseUrl();
  await page.route(`${apiBase}/api/v1/chat/history**`, async (route) => {
    if (route.request().method() === "DELETE") {
      await route.fulfill({ status: 204 });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], has_more: false, next_before_id: null }),
    });
  });
  await page.route(`${apiBase}/api/v1/chat/message`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: [
        `event: token\ndata: ${JSON.stringify({ content: "Bạn đã chi " })}`,
        `event: token\ndata: ${JSON.stringify({ content: "400.000 VND từ transactions confirmed." })}`,
        `event: done\ndata: ${JSON.stringify({})}`,
        "",
      ].join("\n\n"),
    });
  });
}

test.describe("UI core screens API mapping", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page);
  });

  test("analytics renders transaction-source metrics", async ({ page }) => {
    await mockAnalytics(page);
    await page.goto("/analytics");
    await expect(page.getByRole("heading", { name: "Phân tích chi tiêu" })).toBeVisible();
    await expect(page.getByText("400.000 VND").first()).toBeVisible();
    await expect(page.getByText("Chi tiêu cafe tăng mạnh")).toBeVisible();
    // Merchants nằm trong tab Danh mục.
    await page.getByRole("button", { name: "Danh mục" }).click();
    await expect(page.getByText("Highlands Coffee").first()).toBeVisible();
  });

  test("budgets renders usage from transactions", async ({ page }) => {
    await mockBudgets(page);
    await page.goto("/budgets");
    await expect(page.getByRole("heading", { name: "Quản lý ngân sách", exact: true })).toBeVisible();
    await expect(page.getByText("300.000 VND")).toBeVisible();
    await expect(page.getByText("Sắp vượt").first()).toBeVisible();
    await expect(page.getByRole("listitem").filter({ hasText: "Ăn uống" })).toBeVisible();
  });

  test("insights renders evidence-backed feed and can generate", async ({ page }) => {
    await mockInsights(page);
    await page.goto("/insights");
    await expect(page.getByRole("heading", { name: "Thông tin Insights" })).toBeVisible();
    await expect(page.getByText("Ăn uống vượt ngưỡng")).toBeVisible();
    await page.getByRole("button", { name: "Tạo insight mới" }).click();
    await expect(page.getByText("Đã tạo 1 insight mới từ dữ liệu giao dịch.")).toBeVisible();
  });

  test("settings renders control-center operational data", async ({ page }) => {
    await mockSettings(page);
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Cài Đặt Hệ Thống" })).toBeVisible();
    await expect(page.getByText("Free").first()).toBeVisible();
    await expect(page.getByText("settings.updated")).toBeVisible();
    await expect(page.getByText("ui-test@example.com").first()).toBeVisible();
  });

  test("assistant sends a question and renders streamed answer", async ({ page }) => {
    await mockChat(page);
    await page.goto("/chat");
    await expect(page.getByRole("heading", { name: "Trợ lý tài chính (AI)" })).toBeVisible();
    await page.getByPlaceholder("Nhập câu hỏi...").fill("Tháng này tôi tiêu bao nhiêu?");
    await page.getByRole("button", { name: "Gửi" }).click();
    await expect(page.getByText("Bạn đã chi 400.000 VND từ transactions confirmed.")).toBeVisible();
  });
});
