import { expect, test } from "@playwright/test";
import { gotoRoute, resetBrowserState } from "./helpers";

interface VisualRoute {
  path: string;
  heading: string;
  readyHeading?: string | RegExp;
  snapshot: string;
}

const ROUTES: VisualRoute[] = [
  { path: "/", heading: "Command Center", snapshot: "command-center.png" },
  { path: "/services", heading: "Services", snapshot: "services-console.png" },
  { path: "/gpu", heading: "GPU Metrics", snapshot: "gpu-console.png" },
  { path: "/chat", heading: "Direct Chat", snapshot: "direct-chat.png" },
  { path: "/agents", heading: "Agent Console", snapshot: "agent-console.png" },
  { path: "/activity?status=pending_approval", heading: "Activity Feed", snapshot: "history-activity.png" },
  {
    path: "/review?selection=task-eoq-1",
    heading: "Code Review",
    readyHeading: /Implement the next EoBQ scene renderer state machine/i,
    snapshot: "intelligence-review.png",
  },
  { path: "/preferences", heading: "Preferences", snapshot: "memory-preferences.png" },
  {
    path: "/monitoring?panel=grafana",
    heading: "Monitoring",
    readyHeading: /Grafana/i,
    snapshot: "monitoring-console.png",
  },
  {
    path: "/gallery?selection=gallery-1",
    heading: "Gallery",
    readyHeading: /EoBQ\/character/i,
    snapshot: "gallery-console.png",
  },
  {
    path: "/home?panel=lights",
    heading: "Home",
    readyHeading: "Lights",
    snapshot: "home-console.png",
  },
  { path: "/more", heading: "All Pages", snapshot: "route-index.png" },
];

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

for (const route of ROUTES) {
  test(`matches ${route.snapshot}`, async ({ page }) => {
    await gotoRoute(page, route.path, route.heading);

    if (route.readyHeading) {
      await expect(page.locator("main")).toContainText(route.readyHeading);
    }

    if (route.path === "/") {
      await expect(page.locator("main")).toContainText("Unified stream");
      await expect(page.locator("main")).toContainText("Work Plan");
      await page.waitForTimeout(1000);
    }

    await expect(page).toHaveScreenshot(route.snapshot, {
      fullPage: true,
      mask: [page.locator("[data-volatile]")],
      maxDiffPixelRatio: 0.01,
    });
  });
}
