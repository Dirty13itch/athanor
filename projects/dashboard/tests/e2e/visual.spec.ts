import { expect, test } from "@playwright/test";
import { gotoRoute, resetBrowserState } from "./helpers";

const ROUTES = [
  { path: "/", heading: "Command Center", snapshot: "command-center.png" },
  { path: "/services", heading: "Services", snapshot: "services-console.png" },
  { path: "/gpu", heading: "GPU Metrics", snapshot: "gpu-console.png" },
  { path: "/chat", heading: "Direct Chat", snapshot: "direct-chat.png" },
  { path: "/agents", heading: "Agent Console", snapshot: "agent-console.png" },
] as const;

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

for (const route of ROUTES) {
  test(`matches ${route.snapshot}`, async ({ page }) => {
    await gotoRoute(page, route.path, route.heading);

    await expect(page).toHaveScreenshot(route.snapshot, {
      fullPage: true,
      mask: [page.locator("[data-volatile]")],
      maxDiffPixelRatio: 0.01,
    });
  });
}
