import { defineConfig, devices } from "@playwright/test";

const playwrightPort = Number.parseInt(process.env.PLAYWRIGHT_PORT ?? "3005", 10);
const playwrightDistDir =
  process.env.PLAYWRIGHT_NEXT_DIST_DIR ??
  `.next-playwright-${Number.isNaN(playwrightPort) ? 3005 : playwrightPort}`;
const baseUrl = `http://127.0.0.1:${Number.isNaN(playwrightPort) ? 3005 : playwrightPort}`;
const nextDevBundler = process.env.PLAYWRIGHT_NEXT_DEV_BUNDLER ?? "webpack";
const nextDevBundlerArgs = nextDevBundler === "webpack" ? "--webpack" : "";

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
    baseURL: baseUrl,
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
      `powershell -NoProfile -Command "$env:DASHBOARD_FIXTURE_MODE='1'; $env:PLAYWRIGHT_NEXT_DIST_DIR='${playwrightDistDir}'; $env:NEXT_PUBLIC_VAPID_PUBLIC_KEY='BEl6dGVzdF92YXBpZF9wdWJsaWNfa2V5X2Zvcl9wbGF5d3JpZ2h0X19fX19fX19fXw'; npx next dev ${nextDevBundlerArgs} --hostname 127.0.0.1 --port ${Number.isNaN(playwrightPort) ? 3005 : playwrightPort}"`,
    url: baseUrl,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
