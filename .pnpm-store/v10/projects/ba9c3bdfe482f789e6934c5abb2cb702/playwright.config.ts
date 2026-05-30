import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config cho E2E tests Phase 3.11.
 *
 * Pre-requisites khi chạy:
 * 1. Backend API đang chạy trên http://localhost:8000 với DB sạch (xem
 *    `infra/docker/docker-compose.yml` + Alembic migrations).
 * 2. Worker không bắt buộc cho phần lớn test (chỉ upload→review-real cần).
 *    Các test review form đã mock OCR draft endpoint để không phụ thuộc worker.
 *
 * Run:
 *   pnpm exec playwright test
 *
 * Webserver block dưới đây tự khởi động Next.js dev server. Backend phải
 * tự chạy trước (nếu Playwright start luôn cả backend, sẽ phức tạp khi
 * Windows + uv environment; tách ra để dev rõ ràng).
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3100",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    // Dùng port khác (3100) để tránh conflict với dev server đang chạy.
    command: "pnpm exec next dev --port 3100",
    url: "http://localhost:3100",
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
    env: {
      NEXT_PUBLIC_API_BASE_URL:
        process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
    },
  },
});
