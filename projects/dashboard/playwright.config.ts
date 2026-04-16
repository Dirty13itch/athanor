import { defineConfig, devices } from "@playwright/test";

const configuredPlaywrightPort = Number.parseInt(process.env.PLAYWRIGHT_PORT ?? "", 10);
const playwrightPort = Number.isNaN(configuredPlaywrightPort)
  ? 39_000 + (process.pid % 1_000)
  : configuredPlaywrightPort;
const playwrightDistDir =
  process.env.PLAYWRIGHT_NEXT_DIST_DIR ??
  `.next-playwright-${playwrightPort}`;
const baseUrl = `http://127.0.0.1:${playwrightPort}`;
const nextDevBundler = process.env.PLAYWRIGHT_NEXT_DEV_BUNDLER ?? "webpack";
const nextDevBundlerArgs = nextDevBundler === "webpack" ? "--webpack" : "";
const operatorToken = process.env.PLAYWRIGHT_OPERATOR_TOKEN ?? "playwright-operator-token";
const configuredBridgePort = Number.parseInt(process.env.PLAYWRIGHT_WS_PTY_BRIDGE_PORT ?? "", 10);
const bridgePort = Number.isNaN(configuredBridgePort)
  ? 31_000 + (process.pid % 1_000)
  : configuredBridgePort;
const bridgeUrl = process.env.PLAYWRIGHT_WS_PTY_BRIDGE_URL ?? `http://127.0.0.1:${bridgePort}`;
const bridgeTicketSecret =
  process.env.PLAYWRIGHT_WS_PTY_BRIDGE_TICKET_SECRET ?? "playwright-bridge-ticket-secret";

process.env.PLAYWRIGHT_BASE_URL = baseUrl;
process.env.PLAYWRIGHT_OPERATOR_TOKEN = operatorToken;
process.env.PLAYWRIGHT_PORT = String(playwrightPort);
process.env.PLAYWRIGHT_WS_PTY_BRIDGE_PORT = String(bridgePort);
process.env.PLAYWRIGHT_WS_PTY_BRIDGE_URL = bridgeUrl;
process.env.PLAYWRIGHT_WS_PTY_BRIDGE_TICKET_SECRET = bridgeTicketSecret;

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
      `powershell -NoProfile -Command "$env:DASHBOARD_FIXTURE_MODE='1'; $env:DASHBOARD_REQUIRE_OPERATOR_SESSION='1'; $env:ATHANOR_DASHBOARD_OPERATOR_TOKEN='${operatorToken}'; $env:ATHANOR_WS_PTY_BRIDGE_URL='${bridgeUrl}'; $env:ATHANOR_WS_PTY_BRIDGE_ALLOWED_NODES='workshop'; $env:ATHANOR_WS_PTY_BRIDGE_TICKET_SECRET='${bridgeTicketSecret}'; $env:PLAYWRIGHT_NEXT_DIST_DIR='${playwrightDistDir}'; $env:NEXT_PUBLIC_VAPID_PUBLIC_KEY='BEl6dGVzdF92YXBpZF9wdWJsaWNfa2V5X2Zvcl9wbGF5d3JpZ2h0X19fX19fX19fXw'; npx next dev ${nextDevBundlerArgs} --hostname 127.0.0.1 --port ${playwrightPort}"`,
    url: baseUrl,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
