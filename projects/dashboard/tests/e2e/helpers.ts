import { expect, type Page } from "@playwright/test";

export async function resetBrowserState(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });
}

export async function gotoRoute(page: Page, path: string, heading: string) {
  let lastError: unknown;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      lastError = null;
      break;
    } catch (error) {
      lastError = error;
      await page.waitForTimeout(500);
    }
  }

  if (lastError) {
    throw lastError;
  }

  await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
  await page.waitForTimeout(250);
}

export async function mockChatStream(page: Page, events: Array<Record<string, unknown>>) {
  const body = events
    .map((event) => `data: ${JSON.stringify(event)}\n\n`)
    .join("");

  await page.route("**/api/chat", async (route) => {
    await route.fulfill({
      status: 200,
      headers: {
        "cache-control": "no-cache",
        "content-type": "text/event-stream",
      },
      body,
    });
  });
}
