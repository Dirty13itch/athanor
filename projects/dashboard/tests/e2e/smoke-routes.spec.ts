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
  { label: "Dashboard", path: /\/$/, heading: "Command Center" },
  { label: "Monitoring", path: /\/monitoring$/, heading: "Monitoring" },
  { label: "Agents", path: /\/agents$/, heading: "Agent Console" },
  { label: "Media", path: /\/media$/, heading: "Media" },
  { label: "Tasks", path: /\/tasks$/, heading: "Task Board" },
  { label: "Outputs", path: /\/outputs$/, heading: /Outputs/i },
  { label: "Personal Data", path: /\/personal-data$/, heading: "Personal Data" },
  { label: "Preferences", path: /\/preferences$/, heading: "Preferences" },
];

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
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/more", "All Pages");

  for (const link of MORE_LINKS) {
    await page.locator("main").getByRole("link", { name: link.label }).click();
    await expect(page).toHaveURL(link.path);
    await expect(page.locator("main h1")).toContainText(link.heading);
    await page.goBack();
    await expect(page).toHaveURL(/\/more$/);
    await expect(page.getByRole("heading", { name: "All Pages" })).toBeVisible();
  }

  expectNoRuntimeIssues(tracker);
});
