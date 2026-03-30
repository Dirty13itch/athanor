import { expect, test } from "@playwright/test";
import { gotoRoute, resetBrowserState } from "./helpers";

async function navigateFromShell(
  page: import("@playwright/test").Page,
  href: string,
  heading: string
) {
  const mobileNavButton = page.getByRole("button", { name: "Open navigation" });
  const mobileOpen = await mobileNavButton.isVisible();
  if (mobileOpen) {
    await mobileNavButton.click();
  }

  const navRoot = mobileOpen ? page.getByRole("dialog").last() : page.locator("aside").first();
  await navRoot.locator(`a[href="${href}"]`).first().click();
  await expect(page).toHaveURL(
    new RegExp(`${href === "/" ? "/" : href.replace(/\//g, "\\/")}(?:\\?.*)?$`),
    { timeout: 20_000 }
  );
  await expect(page.getByRole("heading", { level: 1 })).toContainText(heading, { timeout: 15_000 });
}

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

test("navigates core routes from the shell", async ({ page }) => {
  for (const [href, heading] of [
    ["/services", "Services"],
    ["/gpu", "GPU Metrics"],
    ["/chat", "Direct Chat"],
  ] as const) {
    await gotoRoute(page, "/", "Command Center");
    await navigateFromShell(page, href, heading);
  }
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

  const launchableRouteTiles = [
    "/services",
    "/governor",
    "/agents",
    "/pipeline",
    "/media",
    "/preferences",
  ];

  for (const href of launchableRouteTiles) {
    await page.getByTestId(
      href === "/" ? "route-index-root" : `route-index-${href.replace(/\//g, "-").replace(/^-+/, "")}`
    ).click();
    await expect(page).not.toHaveURL(/\/more(?:\?.*)?$/, { timeout: 20_000 });
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 15_000 });
    await page.goBack();
    await expect(page).toHaveURL(/\/more(?:\?.*)?$/, { timeout: 20_000 });
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

  await page.locator("select").selectOption("workshop");
  await expect(page.getByText("Workshop (WORKSHOP)")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Terminal" })).toBeVisible();
});
