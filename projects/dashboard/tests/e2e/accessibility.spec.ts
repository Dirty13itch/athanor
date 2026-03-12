import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { loadRouteAuditRecords } from "./census";
import { gotoRoute, resetBrowserState } from "./helpers";

const ROUTES = loadRouteAuditRecords().map((route) => ({
  path: route.routePath,
  heading: route.title,
}));

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

for (const route of ROUTES) {
  test(`has no critical accessibility violations on ${route.path}`, async ({ page }) => {
    await gotoRoute(page, route.path, route.heading);

    const results = await new AxeBuilder({ page }).include("main").analyze();
    expect(results.violations).toEqual([]);
  });
}
