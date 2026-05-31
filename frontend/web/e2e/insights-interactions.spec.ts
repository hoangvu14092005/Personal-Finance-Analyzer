import { expect, test, type Page } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser } from "./helpers";

const now = "2026-05-29T08:00:00Z";

function insight(id: number, severity: string, status = "active") {
  return {
    id, type: "budget_risk", severity, status,
    title: `Insight ${id}`, summary: "Nội dung insight mẫu.",
    evidence: [{ category: "Ăn uống", spent: 240000 }], actions: [],
    range_start: "2026-05-01", range_end: "2026-05-29",
    dismissed_at: null, created_at: now, updated_at: now,
  };
}

async function mockInsights(page: Page, opts: { empty?: boolean } = {}) {
  const api = backendBaseUrl();
  await mockAuthenticatedUser(page);
  // Single dispatcher for all /insights* requests to avoid route-precedence ambiguity.
  await page.route(`${api}/api/v1/insights**`, async (route) => {
    const req = route.request();
    const method = req.method();
    const url = req.url();
    const json = (body: object, status = 200) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

    if (url.includes("/insights/generate") && method === "POST") {
      await json({ items: [insight(1, "warning")], generated_count: 1 });
      return;
    }
    if (url.includes("/feedback") && method === "POST") {
      await json({ id: 1, insight_id: 1, rating: "helpful", comment: null, created_at: now });
      return;
    }
    if (method === "PATCH") {
      await json(insight(1, "warning", "dismissed"));
      return;
    }
    // GET list
    const items = opts.empty ? [] : [insight(1, "warning"), insight(2, "danger")];
    await json({ items, has_more: false, next_before_id: null });
  });
}

test.describe("Insights interactions", () => {
  test("renders insight feed", async ({ page }) => {
    await mockInsights(page);
    await page.goto("/insights");
    await expect(page.getByRole("heading", { name: "Thông tin Insights" })).toBeVisible();
    await expect(page.getByText("Insight 1")).toBeVisible();
  });

  test("generate button creates insight and shows notice", async ({ page }) => {
    await mockInsights(page, { empty: true });
    await page.goto("/insights");
    await page.getByRole("button", { name: "Tạo insight mới" }).click();
    await expect(page.getByText("Đã tạo 1 insight mới từ dữ liệu giao dịch.")).toBeVisible();
  });

  test("filter tabs switch active filter", async ({ page }) => {
    await mockInsights(page);
    await page.goto("/insights");
    await page.getByRole("button", { name: "Rủi ro cao" }).click();
    await expect(page.getByText("Insight 1")).toBeVisible();
  });

  test("helpful feedback shows acknowledgement", async ({ page }) => {
    await mockInsights(page);
    await page.goto("/insights");
    await page.getByRole("button", { name: "Hữu ích" }).first().click();
    await expect(page.getByText("Đã ghi nhận insight hữu ích.")).toBeVisible();
  });

  test("dismiss insight shows notice", async ({ page }) => {
    await mockInsights(page);
    await page.goto("/insights");
    await page.getByRole("button", { name: "Ẩn", exact: true }).first().click();
    await expect(page.getByText("Insight đã được ẩn khỏi feed hoạt động.")).toBeVisible();
  });
});
