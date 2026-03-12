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

  await page.waitForLoadState("networkidle", { timeout: 3_000 }).catch(() => undefined);
  const headingLocator = page.locator("main h1");
  await expect(headingLocator).toBeVisible({ timeout: 15_000 });
  await expect(headingLocator).not.toHaveText(/^\s*$/);
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
  await page.waitForTimeout(250);
}

export interface RuntimeIssueTracker {
  consoleErrors: string[];
  failedRequests: string[];
  failedExternalRequests: string[];
  pageErrors: string[];
  serverErrors: string[];
}

export function trackRuntimeIssues(page: Page): RuntimeIssueTracker {
  const tracker: RuntimeIssueTracker = {
    consoleErrors: [],
    failedRequests: [],
    failedExternalRequests: [],
    pageErrors: [],
    serverErrors: [],
  };

  page.on("console", (message) => {
    if (message.type() === "error") {
      if (/^Failed to load resource: net::ERR_CONNECTION_FAILED/.test(message.text())) {
        return;
      }
      tracker.consoleErrors.push(message.text());
    }
  });

  page.on("pageerror", (error) => {
    tracker.pageErrors.push(error.message);
  });

  page.on("requestfailed", (request) => {
    const errorText = request.failure()?.errorText ?? "failed";
    if (errorText.includes("ERR_ABORTED")) {
      return;
    }

    const entry = `${request.method()} ${request.url()}: ${errorText}`;
    if (request.url().startsWith("http://127.0.0.1:3005")) {
      tracker.failedRequests.push(entry);
    } else {
      tracker.failedExternalRequests.push(entry);
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
    tracker.failedExternalRequests,
    `Unexpected failed external requests:\n${tracker.failedExternalRequests.join("\n")}`
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

export async function installClipboardMock(page: Page) {
  await page.addInitScript(() => {
    const clipboardState = { text: "" };

    Object.defineProperty(window, "__athanorClipboardState", {
      configurable: true,
      value: clipboardState,
    });

    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: async (value: string) => {
          clipboardState.text = value;
        },
        readText: async () => clipboardState.text,
      },
    });
  });
}

export async function readClipboardText(page: Page) {
  return page.evaluate(() => {
    const state = (
      window as typeof window & {
        __athanorClipboardState?: { text: string };
      }
    ).__athanorClipboardState;

    return state?.text ?? "";
  });
}

export interface CapturedExport {
  filename: string;
  href: string;
  mimeType: string;
  text: string;
}

export async function installExportCapture(page: Page) {
  await page.addInitScript(() => {
    const exportState = {
      entries: [] as Array<{ filename: string; href: string; mimeType: string; text: string }>,
      pending: [] as Array<Promise<void>>,
    };
    const blobUrls = new Map<string, Blob>();
    const originalCreateObjectURL = URL.createObjectURL.bind(URL);
    const originalRevokeObjectURL = URL.revokeObjectURL.bind(URL);
    const originalClick = HTMLAnchorElement.prototype.click;
    let counter = 0;

    Object.defineProperty(window, "__athanorExportState", {
      configurable: true,
      value: exportState,
    });

    URL.createObjectURL = (value: Blob | MediaSource) => {
      if (value instanceof Blob) {
        const blobUrl = `blob:athanor-export-${counter++}`;
        blobUrls.set(blobUrl, value);
        return blobUrl;
      }

      return originalCreateObjectURL(value);
    };

    URL.revokeObjectURL = (url: string) => {
      if (blobUrls.has(url)) {
        blobUrls.delete(url);
        return;
      }

      return originalRevokeObjectURL(url);
    };

    HTMLAnchorElement.prototype.click = function click() {
      const blob = blobUrls.get(this.href);
      if (blob && this.download) {
        const entry = {
          filename: this.download,
          href: this.href,
          mimeType: blob.type,
          text: "",
        };
        const pending = blob.text().then((text) => {
          entry.text = text;
          exportState.entries.push(entry);
        });
        exportState.pending.push(pending);
        return;
      }

      return originalClick.call(this);
    };
  });
}

export async function waitForCapturedExport(page: Page, index = 0): Promise<CapturedExport> {
  await expect
    .poll(() =>
      page.evaluate(() => {
        const state = (
          window as typeof window & {
            __athanorExportState?: { entries: unknown[] };
          }
        ).__athanorExportState;

        return state?.entries.length ?? 0;
      })
    )
    .toBeGreaterThan(index);

  return page.evaluate(async (entryIndex) => {
    const state = (
      window as typeof window & {
        __athanorExportState?: {
          entries: CapturedExport[];
          pending: Array<Promise<void>>;
        };
      }
    ).__athanorExportState;

    if (!state) {
      throw new Error("Missing export capture state");
    }

    await Promise.all(state.pending);
    state.pending = [];
    return state.entries[entryIndex];
  }, index);
}
