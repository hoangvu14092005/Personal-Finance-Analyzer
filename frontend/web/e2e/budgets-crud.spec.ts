import { expect, test, type Page } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser, mockCategories } from "./helpers";

const now = "2026-05-29T08:00:00Z";

/**
 * Budgets screen — create / validate / edit / delete buttons + usage display.
 * Uses a stateful in-memory mock so create/delete reflect in subsequent reads.
 */
async function mockBudgetsApi(page: Page, opts: { startEmpty?: boolean } = {}) {
  const api = backendBaseUrl();
  await mockAuthenticatedUser(page);
  await mockCategories(page);

  let budgets: Array<Record<string, unknown>> = opts.startEmpty
    ? []
    : [{ id: 10, user_id: 1, category_id: 1, period_month: "2026-05", amount: "300000", created_at: now, updated_at: now }];

  await page.route(`${api}/api/v1/budgets**`, async (route) => {
    const req = route.request();
    const method = req.method();
    const url = req.url();
    const json = (body: object, status = 200) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

    // Usage endpoint (GET /budgets/usage).
    if (url.includes("/budgets/usage")) {
      const usage = budgets.map((b) => ({
        budget_id: b.id, category_id: b.category_id, category_name: "Ăn uống",
        category_color: "#2c8c66", period_month: b.period_month,
        budget_amount: b.amount, spent_amount: "270000", remaining_amount: "30000",
        percent_used: 90, status: "warning",
      }));
      await json(usage);
      return;
    }
    if (method === "GET") {
      await json({ items: budgets });
      return;
    }
    if (method === "POST") {
      const payload = req.postDataJSON() as Record<string, unknown>;
      const created = { id: 99, user_id: 1, created_at: now, updated_at: now, ...payload };
      budgets = [...budgets, created];
      await json(created, 201);
      return;
    }
    if (method === "PUT") {
      const id = Number(url.split("/").pop());
      const payload = req.postDataJSON() as Record<string, unknown>;
      budgets = budgets.map((b) => (b.id === id ? { ...b, ...payload } : b));
      await json(budgets.find((b) => b.id === id) ?? {});
      return;
    }
    if (method === "DELETE") {
      const id = Number(url.split("/").pop());
      budgets = budgets.filter((b) => b.id !== id);
      await route.fulfill({ status: 204 });
      return;
    }
    await route.fallback();
  });
}

test.describe("Budgets CRUD", () => {
  test("renders budgets list and usage", async ({ page }) => {
    await mockBudgetsApi(page);
    await page.goto("/budgets");
    await expect(page.getByRole("heading", { name: "Quản lý ngân sách", exact: true })).toBeVisible();
    await expect(page.getByText("300.000", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("Sắp vượt").first()).toBeVisible();
  });

  test("validation: amount must be positive", async ({ page }) => {
    await mockBudgetsApi(page, { startEmpty: true });
    await page.goto("/budgets");
    // Fill an invalid non-positive amount to bypass HTML required and trigger JS validation.
    await page.getByPlaceholder("VD: 2000000").fill("0");
    await page.getByRole("button", { name: "Thêm ngân sách" }).click();
    await expect(page.getByText("Số tiền phải là số dương.")).toBeVisible();
  });

  test("create a new budget appears in list", async ({ page }) => {
    await mockBudgetsApi(page, { startEmpty: true });
    await page.goto("/budgets");
    await page.locator("select").first().selectOption("1");
    await page.getByPlaceholder("VD: 2000000").fill("500000");
    await page.getByRole("button", { name: "Thêm ngân sách" }).click();
    // New budget row appears in the list section (heading "Ngân sách tháng ...").
    await expect(page.getByText("Đã dùng:", { exact: false })).toBeVisible();
  });

  test("edit button enters edit mode with cancel", async ({ page }) => {
    await mockBudgetsApi(page);
    await page.goto("/budgets");
    await page.getByRole("button", { name: "Sửa" }).first().click();
    await expect(page.getByRole("button", { name: "Cập nhật" })).toBeVisible();
    await page.getByRole("button", { name: "Huỷ sửa" }).click();
    await expect(page.getByRole("button", { name: "Thêm ngân sách" })).toBeVisible();
  });

  test("delete button removes budget after confirm", async ({ page }) => {
    await mockBudgetsApi(page);
    page.on("dialog", (dialog) => dialog.accept());
    await page.goto("/budgets");
    await page.getByRole("button", { name: "Xoá" }).first().click();
    await expect(page.getByText("Chưa có ngân sách nào cho tháng này.", { exact: false })).toBeVisible();
  });
});
