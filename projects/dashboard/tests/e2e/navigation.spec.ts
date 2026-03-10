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

  await page.getByRole("link", { name: label }).click();
  await expect(page).toHaveURL(destination);
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

test("round-trips every /more route tile without losing the route index", async ({ page }) => {
  test.slow();
  await gotoRoute(page, "/more", "All Pages");

  const routeTiles = await page.locator("main a[href^='/']").evaluateAll((elements) =>
    elements.map((element) => ({
      href: element.getAttribute("href") ?? "",
      label: element.getAttribute("aria-label") ?? "",
    }))
  );

  for (const routeTile of routeTiles) {
    await page.locator(`main a[href="${routeTile.href}"]`).first().click();
    await expect(page).not.toHaveURL(/\/more(?:\?.*)?$/);
    await expect(page.locator("main h1")).toBeVisible();
    await page.goBack();
    await expect(page).toHaveURL(/\/more(?:\?.*)?$/);
    await expect(page.getByRole("heading", { name: "All Pages" })).toBeVisible();
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

  await expect(page.getByText("WebSocket connection failed. Terminal bridge may not be running.")).toBeVisible();
  await expect(page.getByText("Disconnected")).toBeVisible();

  await page.locator("select").selectOption("node2");
  await expect(page.getByText("Workshop (node2)")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Terminal" })).toBeVisible();
});
