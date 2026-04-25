import { expect, test } from "@playwright/test";

import { registerAndLogin } from "./helpers";

test.describe("Auth flow", () => {
  test("user can register, login, and reach dashboard", async ({ page }) => {
    await registerAndLogin(page, { fullName: "E2E Smoke" });

    // Dashboard hiển thị nav links + main content.
    await expect(page.getByRole("link", { name: "Transactions" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Upload" })).toBeVisible();
    await expect(page.getByRole("link", { name: "New Entry" })).toBeVisible();
  });
});
