import { expect, type Page } from "@playwright/test";

export async function resetBrowserState(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });
}

export async function gotoRoute(page: Page, path: string, heading: RegExp | string) {
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

export interface RuntimeIssueTracker {
  consoleErrors: string[];
  failedRequests: string[];
  pageErrors: string[];
  serverErrors: string[];
}

export function trackRuntimeIssues(page: Page): RuntimeIssueTracker {
  const tracker: RuntimeIssueTracker = {
    consoleErrors: [],
    failedRequests: [],
    pageErrors: [],
    serverErrors: [],
  };

  page.on("console", (message) => {
    if (message.type() === "error") {
      tracker.consoleErrors.push(message.text());
    }
  });

  page.on("pageerror", (error) => {
    tracker.pageErrors.push(error.message);
  });

  page.on("requestfailed", (request) => {
    const errorText = request.failure()?.errorText ?? "failed";
    if (
      request.url().startsWith("http://127.0.0.1:3005") &&
      !errorText.includes("ERR_ABORTED")
    ) {
      tracker.failedRequests.push(`${request.method()} ${request.url()}: ${errorText}`);
    }
  });

  page.on("response", (response) => {
    if (
      response.url().startsWith("http://127.0.0.1:3005") &&
      response.status() >= 500
    ) {
      tracker.serverErrors.push(`${response.status()} ${response.url()}`);
    }
  });

  return tracker;
}

export function expectNoRuntimeIssues(tracker: RuntimeIssueTracker) {
  expect(
    tracker.pageErrors,
    `Unexpected page errors:\n${tracker.pageErrors.join("\n")}`
  ).toEqual([]);
  expect(
    tracker.consoleErrors,
    `Unexpected console errors:\n${tracker.consoleErrors.join("\n")}`
  ).toEqual([]);
  expect(
    tracker.failedRequests,
    `Unexpected failed same-origin requests:\n${tracker.failedRequests.join("\n")}`
  ).toEqual([]);
  expect(
    tracker.serverErrors,
    `Unexpected same-origin 5xx responses:\n${tracker.serverErrors.join("\n")}`
  ).toEqual([]);
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
