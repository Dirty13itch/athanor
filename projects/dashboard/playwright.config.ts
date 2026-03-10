import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 2,
  reporter: "list",
  expect: {
    toHaveScreenshot: {
      animations: "disabled",
      caret: "hide",
      scale: "css",
    },
  },
  use: {
    baseURL: "http://127.0.0.1:3005",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "desktop-chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "mobile-chromium",
      use: { ...devices["Pixel 7"] },
    },
  ],
  webServer: {
    command:
      "powershell -NoProfile -Command \"$env:DASHBOARD_FIXTURE_MODE='1'; $env:NEXT_PUBLIC_VAPID_PUBLIC_KEY='BEl6dGVzdF92YXBpZF9wdWJsaWNfa2V5X2Zvcl9wbGF5d3JpZ2h0X19fX19fX19fXw'; npx next dev --hostname 127.0.0.1 --port 3005\"",
    url: "http://127.0.0.1:3005",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
