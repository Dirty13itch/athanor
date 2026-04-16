import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3006",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "desktop-chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "EOQ_FIXTURE_MODE=1 npx next dev --hostname 127.0.0.1 --port 3006",
    url: "http://127.0.0.1:3006",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
