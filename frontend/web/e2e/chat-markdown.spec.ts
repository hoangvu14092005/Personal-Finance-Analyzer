import { expect, test, type Page } from "@playwright/test";

import { backendBaseUrl, mockAuthenticatedUser } from "./helpers";

/**
 * Chat assistant — markdown rendering fix + interactions.
 * Verifies that markdown (**bold**, lists) renders as HTML, not raw asterisks.
 */
async function mockChatHistory(page: Page, opts: { withMarkdown?: boolean } = {}) {
  const api = backendBaseUrl();
  await mockAuthenticatedUser(page);
  await page.route(`${api}/api/v1/chat/history**`, async (route) => {
    if (route.request().method() === "DELETE") {
      await route.fulfill({ status: 204 });
      return;
    }
    const items = opts.withMarkdown
      ? [
          { id: 1, role: "user", content: "Tổng chi tháng này", tool_calls: null, tool_name: null, created_at: "2026-05-29T08:00:00Z" },
          {
            id: 2, role: "assistant",
            content: "Tháng này bạn chi nhiều nhất cho **Mua sắm: 420.000 VND**.\n\n- **Hóa đơn:** 310.000 VND\n- **Di chuyển:** 125.000 VND",
            tool_calls: null, tool_name: null, created_at: "2026-05-29T08:00:01Z",
          },
        ]
      : [];
    await route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ items, has_more: false, next_before_id: null }),
    });
  });
}

async function mockChatStream(page: Page) {
  const api = backendBaseUrl();
  await page.route(`${api}/api/v1/chat/message`, async (route) => {
    await route.fulfill({
      status: 200, contentType: "text/event-stream",
      body: [
        `event: token\ndata: ${JSON.stringify({ content: "Bạn đã chi **400.000 VND** " })}`,
        `event: token\ndata: ${JSON.stringify({ content: "từ giao dịch đã xác nhận." })}`,
        `event: done\ndata: ${JSON.stringify({})}`,
        "",
      ].join("\n\n"),
    });
  });
}

test.describe("Chat assistant markdown", () => {
  test("renders bold markdown as <strong>, not raw asterisks", async ({ page }) => {
    await mockChatHistory(page, { withMarkdown: true });
    await mockChatStream(page);
    await page.goto("/chat");
    // Bold text rendered without surrounding asterisks.
    await expect(page.getByText("Mua sắm: 420.000 VND", { exact: false })).toBeVisible();
    const strong = page.locator(".chat-markdown strong", { hasText: "Mua sắm: 420.000 VND" });
    await expect(strong).toBeVisible();
    // Raw markdown markers must NOT appear as visible text.
    await expect(page.getByText("**Mua sắm", { exact: false })).toHaveCount(0);
  });

  test("renders list items from markdown", async ({ page }) => {
    await mockChatHistory(page, { withMarkdown: true });
    await mockChatStream(page);
    await page.goto("/chat");
    await expect(page.locator(".chat-markdown li")).toHaveCount(2);
  });

  test("send message renders streamed markdown answer", async ({ page }) => {
    await mockChatHistory(page);
    await mockChatStream(page);
    await page.goto("/chat");
    await page.getByPlaceholder("Nhập câu hỏi...").fill("Tháng này tôi tiêu bao nhiêu?");
    await page.getByRole("button", { name: "Gửi" }).click();
    await expect(page.getByText("từ giao dịch đã xác nhận.", { exact: false })).toBeVisible();
    await expect(page.locator(".chat-markdown strong", { hasText: "400.000 VND" })).toBeVisible();
  });

  test("suggested question chips fill input", async ({ page }) => {
    await mockChatHistory(page);
    await mockChatStream(page);
    await page.goto("/chat");
    await page.getByRole("button", { name: "Tổng chi tháng này" }).first().click();
    await expect(page.getByText("từ giao dịch đã xác nhận.", { exact: false })).toBeVisible();
  });
});
