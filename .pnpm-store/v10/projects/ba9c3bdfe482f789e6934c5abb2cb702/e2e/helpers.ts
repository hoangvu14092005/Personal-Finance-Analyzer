import { expect, Page } from "@playwright/test";

/**
 * Generate email duy nhất cho mỗi test run, tránh đụng dữ liệu user cũ
 * trong DB persistent. Format: `e2e-<timestamp>-<random>@example.com`.
 */
export function uniqueEmail(prefix = "e2e"): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).slice(2, 8);
  return `${prefix}-${timestamp}-${random}@example.com`;
}

/**
 * Đăng ký user mới qua `/register` rồi đăng nhập qua `/login`.
 *
 * Lưu ý: sau khi register thành công, `app/register/page.tsx` redirect về
 * `/login` (không tự auto-login). Helper này tự động làm cả hai bước để
 * test có session và có thể truy cập trang yêu cầu auth.
 */
export async function registerAndLogin(
  page: Page,
  options: { fullName?: string } = {},
): Promise<{ email: string; password: string }> {
  const email = uniqueEmail();
  // Min 8 chars, có chữ + số (theo yêu cầu register form).
  const password = "Test1234abc";

  // --- Register ---
  await page.goto("/register");
  // Label tiếng việt không dấu trong UI hiện tại: "Email", "Ho va ten", "Mat khau".
  await page.getByLabel("Email").fill(email);
  if (options.fullName) {
    await page.getByLabel("Ho va ten").fill(options.fullName);
  }
  await page.getByLabel("Mat khau").fill(password);
  await page.getByRole("button", { name: "Tao tai khoan" }).click();
  await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });

  // --- Login ---
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mat khau").fill(password);
  await page.getByRole("button", { name: "Dang nhap" }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });

  return { email, password };
}

/**
 * Backend API base URL — match với `lib/config.ts` mặc định.
 */
export function backendBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "**";
}

export async function mockAuthenticatedUser(page: Page): Promise<void> {
  const apiBase = backendBaseUrl();
  await page.route(`${apiBase}/api/v1/auth/me`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user: {
          id: 1,
          email: "ui-test@example.com",
          full_name: "UI Tester",
          currency: "VND",
          timezone: "Asia/Ho_Chi_Minh",
          locale: "vi-VN",
        },
      }),
    });
  });
}

export async function mockCategories(page: Page): Promise<void> {
  const apiBase = backendBaseUrl();
  await page.route(`${apiBase}/api/v1/categories`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: 1,
            name: "Ăn uống",
            color: "#2c8c66",
            is_system: true,
            user_id: null,
            created_at: "2026-01-01T00:00:00Z",
          },
          {
            id: 2,
            name: "Di chuyển",
            color: "#2c84e0",
            is_system: true,
            user_id: null,
            created_at: "2026-01-01T00:00:00Z",
          },
        ],
      }),
    });
  });
}
