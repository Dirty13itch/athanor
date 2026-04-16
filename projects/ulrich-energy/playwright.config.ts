import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3007",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "desktop-chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command:
      "powershell -NoProfile -Command \"$env:ULRICH_FIXTURE_MODE='1'; npx next dev --hostname 127.0.0.1 --port 3007\"",
    url: "http://127.0.0.1:3007",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
