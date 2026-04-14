import { expect, test } from "@playwright/test";
import {
  expectNoRuntimeIssues,
  gotoRoute,
  resetBrowserState,
  trackRuntimeIssues,
} from "./helpers";
import { loadRouteAuditRecords } from "./census";

const ROUTES = loadRouteAuditRecords().map((route) => ({
  path: route.routePath,
  heading: route.title,
}));

const MORE_LINKS: Array<{ label: string; path: RegExp; heading: RegExp | string }> = [
  { label: "Command Center", path: /\/$/, heading: /Triage the system|Command Center/i },
  { label: "Monitoring", path: /\/monitoring$/, heading: "Monitoring" },
  { label: "Preferences", path: /\/preferences$/, heading: "Preferences" },
];

function routeIndexTestId(path: RegExp | string) {
  if (path instanceof RegExp) {
    const raw = path.source
      .replace(/^\\\//, "/")
      .replace(/\$$/, "")
      .replace(/\\\//g, "/");
    if (raw === "/") {
      return "route-index-root";
    }
    return `route-index-${raw.replace(/\//g, "-").replace(/^-+/, "")}`;
  }

  if (path === "/") {
    return "route-index-root";
  }

  return `route-index-${path.replace(/\//g, "-").replace(/^-+/, "")}`;
}

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

for (const route of ROUTES) {
  test(`smoke: ${route.path} renders without runtime errors`, async ({ page }) => {
    const tracker = trackRuntimeIssues(page);

    await gotoRoute(page, route.path, route.heading);
    await page.waitForTimeout(900);

    expectNoRuntimeIssues(tracker);
  });
}

test("smoke: /more links navigate and browser back returns to route index", async ({ page }) => {
  test.slow();
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/more", "All Pages");

  for (const link of MORE_LINKS) {
    await page.getByTestId(routeIndexTestId(link.path)).click();
    await expect(page).toHaveURL(link.path, { timeout: 20_000 });
    await expect(page.locator("main h1")).toContainText(link.heading);
    await page.goBack();
    await expect(page).toHaveURL(/\/more$/, { timeout: 20_000 });
    await expect(page.getByRole("heading", { name: "All Pages" })).toBeVisible();
  }

  expectNoRuntimeIssues(tracker);
});
