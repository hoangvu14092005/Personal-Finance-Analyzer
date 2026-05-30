import { expect, test } from "@playwright/test";

test.describe("Environment config", () => {
  test("health page shows API endpoint from env", async ({ page }) => {
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

    await page.goto("/health");

    await expect(page.getByText(`${apiBaseUrl}/health`)).toBeVisible();
  });
});
