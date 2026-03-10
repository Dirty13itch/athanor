import { expect, test } from "@playwright/test";
import {
  expectNoRuntimeIssues,
  gotoRoute,
  resetBrowserState,
  trackRuntimeIssues,
} from "./helpers";

const ROUTES: Array<{ heading: RegExp | string; path: string }> = [
  { path: "/", heading: "Command Center" },
  { path: "/services", heading: "Services" },
  { path: "/gpu", heading: "GPU Metrics" },
  { path: "/chat", heading: "Direct Chat" },
  { path: "/agents", heading: "Agent Console" },
  { path: "/tasks", heading: "Task Board" },
  { path: "/goals", heading: "Goals" },
  { path: "/notifications", heading: "Notifications" },
  { path: "/workplanner", heading: "Work Planner" },
  { path: "/workspace", heading: "Workspace" },
  { path: "/activity", heading: "Activity Feed" },
  { path: "/conversations", heading: "Conversations" },
  { path: "/gallery", heading: "Gallery" },
  { path: "/home", heading: "Home" },
  { path: "/insights", heading: "Insights" },
  { path: "/learning", heading: "Learning Metrics" },
  { path: "/media", heading: "Media" },
  { path: "/monitoring", heading: "Monitoring" },
  { path: "/more", heading: "All Pages" },
  { path: "/outputs", heading: /Outputs/i },
  { path: "/personal-data", heading: "Personal Data" },
  { path: "/preferences", heading: "Preferences" },
  { path: "/review", heading: "Code Review" },
  { path: "/terminal", heading: "Terminal" },
  { path: "/offline", heading: /offline/i },
];

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
    await expect(page.getByRole("heading", { name: link.heading })).toBeVisible();
    await page.goBack();
    await expect(page).toHaveURL(/\/more$/);
    await expect(page.getByRole("heading", { name: "All Pages" })).toBeVisible();
  }

  expectNoRuntimeIssues(tracker);
});
