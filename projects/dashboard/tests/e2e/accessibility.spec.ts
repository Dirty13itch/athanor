import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { gotoRoute, resetBrowserState } from "./helpers";

const ROUTES = [
  { path: "/", heading: "Command Center" },
  { path: "/services", heading: "Services" },
  { path: "/gpu", heading: "GPU Metrics" },
  { path: "/chat", heading: "Direct Chat" },
  { path: "/agents", heading: "Agent Console" },
  { path: "/activity", heading: "Activity Feed" },
  { path: "/review", heading: "Code Review" },
  { path: "/preferences", heading: "Preferences" },
  { path: "/monitoring", heading: "Monitoring" },
  { path: "/home", heading: "Home" },
] as const;

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
