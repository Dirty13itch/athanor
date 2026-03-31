import { expect, test } from "@playwright/test";
import { gotoRoute, resetBrowserState } from "./helpers";

async function navigateFromShell(
  page: import("@playwright/test").Page,
  label: string,
  destination: RegExp,
  heading: string
) {
  const mobileNavButton = page.getByRole("button", { name: "Open navigation" });
  if (await mobileNavButton.isVisible()) {
    await mobileNavButton.click();
  }

  await Promise.all([
    page.waitForURL(destination, { timeout: 20_000 }),
    page.locator(".nav-rail-link").filter({ hasText: label }).first().click(),
  ]);
  await expect(page.locator("main h1")).toContainText(heading);
}

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

test("navigates core routes from the shell", async ({ page }) => {
  await gotoRoute(page, "/", "Command Center");

  await navigateFromShell(page, "Services", /\/services$/, "Services");
  await navigateFromShell(page, "GPU Metrics", /\/gpu$/, "GPU Metrics");
  await navigateFromShell(page, "Direct Chat", /\/chat$/, "Direct Chat");
});

test("opens the command palette and routes to incidents", async ({ page }) => {
  await gotoRoute(page, "/", "Command Center");

  const paletteButton = page.getByRole("button", { name: /command palette|open command palette/i });
  await paletteButton.first().click();
  await expect(page.getByRole("dialog", { name: "Command palette" })).toBeAttached();

  await page.getByPlaceholder("Jump to a route, tool, or priority item").fill("services");
  await page.keyboard.press("Enter");

  await expect(page).toHaveURL(/\/services$/);
  await expect(page.getByRole("heading", { name: "Services" })).toBeVisible();
});

test("indexes every /more route tile and round-trips representative launches", async ({ page }) => {
  await gotoRoute(page, "/more", "All Pages");

  const launchTiles = await page
    .locator("[data-testid='route-index-families'] a[data-testid^='route-index-']:not([data-testid='route-index-more'])")
    .evaluateAll((elements) =>
    elements.map((element) => ({
      testId: element.getAttribute("data-testid") ?? "",
      href: element.getAttribute("href") ?? "",
      label: element.getAttribute("aria-label") ?? "",
    }))
  );

  expect(launchTiles.length).toBeGreaterThan(20);
  expect(new Set(launchTiles.map((routeTile) => routeTile.href)).size).toBe(launchTiles.length);
  expect(launchTiles.every((routeTile) => routeTile.href.startsWith("/"))).toBeTruthy();

  const representativeHrefs = new Set(["/", "/services", "/chat", "/media", "/catalog"]);
  const representativeTiles = launchTiles.filter((routeTile) => representativeHrefs.has(routeTile.href));

  for (const routeTile of representativeTiles) {
    await Promise.all([
      page.waitForURL((url) => url.pathname === routeTile.href, { timeout: 20_000 }),
      page.getByTestId(routeTile.testId).click(),
    ]);
    await expect(page.locator("main h1")).toBeVisible({ timeout: 20_000 });
    await gotoRoute(page, "/more", "All Pages");
  }
});

test("renders terminal fallback state cleanly when the websocket bridge is unavailable", async ({
  page,
}) => {
  await page.addInitScript(() => {
    class MockFailingWebSocket {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSING = 2;
      static CLOSED = 3;

      readyState = MockFailingWebSocket.CONNECTING;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;

      constructor(url: string) {
        void url;
        window.setTimeout(() => {
          this.readyState = MockFailingWebSocket.CLOSED;
          const errorEvent = new Event("error");
          this.onerror?.(errorEvent);
          const closeEvent = new CloseEvent("close");
          this.onclose?.(closeEvent);
        }, 0);
      }

      send() {}

      close() {
        this.readyState = MockFailingWebSocket.CLOSED;
        this.onclose?.(new CloseEvent("close"));
      }
    }

    Object.defineProperty(window, "WebSocket", {
      configurable: true,
      writable: true,
      value: MockFailingWebSocket,
    });
  });

  await gotoRoute(page, "/terminal", "Terminal");

  await expect(page.getByRole("heading", { name: "Terminal" })).toBeVisible();
  await expect(
    page
      .getByText(/Operator terminal access is unavailable/i)
      .or(page.getByText(/Connection failed\.|WebSocket connection failed|Disconnected/i).first())
  ).toBeVisible();
});
