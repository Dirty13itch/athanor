import { expect, test } from "@playwright/test";
import {
  expectNoRuntimeIssues,
  gotoRoute,
  resetBrowserState,
  trackRuntimeIssues,
} from "./helpers";

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

test("history family preserves filters, drawer state, and review back-links", async ({ page }) => {
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/activity", "Activity Feed");

  await page.locator("main").getByRole("button", { name: "Approval" }).first().click();

  await expect(page).toHaveURL(/status=pending_approval/);

  await page
    .locator("button")
    .filter({ hasText: /Reworked the EoBQ scene renderer/i })
    .first()
    .click();

  await expect(page).toHaveURL(/selection=activity-1/);
  await expect(page.getByRole("dialog", { name: /write_scene_renderer/i })).toBeVisible();

  await page.getByRole("link", { name: "Review item" }).click();
  await expect(page).toHaveURL(/\/review\?selection=task-eoq-1$/);
  await expect(page.locator("main h1")).toContainText("Code Review");

  await page.goBack();
  await expect(page).toHaveURL(/\/activity\?/);
  await expect(page).toHaveURL(/status=pending_approval/);
  await expect(page).toHaveURL(/selection=activity-1/);
  await expect(page.getByRole("dialog", { name: /write_scene_renderer/i })).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(page).not.toHaveURL(/selection=activity-1/);

  expectNoRuntimeIssues(tracker);
});

test("intelligence actions run cleanly in fixture mode and support severity filtering", async ({
  page,
}) => {
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/insights", "Insights");

  const runInsightsResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/insights/run") && response.request().method() === "POST";
  });
  await page.getByRole("button", { name: "Run insights" }).click();
  expect((await runInsightsResponse).ok()).toBeTruthy();

  const runBenchmarksResponse = page.waitForResponse((response) => {
    return (
      response.url().includes("/api/learning/benchmarks") &&
      response.request().method() === "POST"
    );
  });
  await page.getByRole("button", { name: "Run benchmarks" }).click();
  expect((await runBenchmarksResponse).ok()).toBeTruthy();

  await page.getByRole("button", { name: "High" }).click();
  await expect(page).toHaveURL(/severity=high/);
  await expect(page.getByText("contract drift")).toBeVisible();

  expectNoRuntimeIssues(tracker);
});

test("review queue keeps selection state, approval actions, and project back-links", async ({
  page,
}) => {
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/review", "Code Review");

  await page.getByRole("button", { name: "Empire of Broken Queens (Featured)" }).click();
  await expect(page).toHaveURL(/project=eoq/);

  await page
    .getByRole("button", {
      name: /Implement the next EoBQ scene renderer state machine and branching transitions/i,
    })
    .click();

  await expect(page).toHaveURL(/selection=task-eoq-1/);
  await expect(
    page.getByRole("dialog", {
      name: /Implement the next EoBQ scene renderer state machine and branching transitions/i,
    })
  ).toBeVisible();

  const approveResponse = page.waitForResponse((response) => {
    return (
      response.url().includes("/api/workforce/tasks/task-eoq-1/approve") &&
      response.request().method() === "POST"
    );
  });
  await page.getByRole("button", { name: "Approve" }).click();
  expect((await approveResponse).ok()).toBeTruthy();

  await page.getByRole("link", { name: "Open project" }).click();
  await expect(page).toHaveURL(/\/workplanner\?project=eoq$/);
  await expect(page.getByRole("heading", { name: "Work Planner" })).toBeVisible();

  await page.goBack();
  await expect(page).toHaveURL(/\/review\?/);
  await expect(page).toHaveURL(/project=eoq/);
  await expect(page).toHaveURL(/selection=task-eoq-1/);
  await expect(
    page.getByRole("dialog", {
      name: /Implement the next EoBQ scene renderer state machine and branching transitions/i,
    })
  ).toBeVisible();

  expectNoRuntimeIssues(tracker);
});

test("preferences supports fixture-safe preference storage", async ({ page }) => {
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/preferences", "Preferences");

  const input = page.getByPlaceholder("Store a new operator preference or constraint");
  await input.fill("Keep the command center focused on project-first execution.");

  const saveResponse = page.waitForResponse((response) => {
    return response.url().includes("/api/preferences") && response.request().method() === "POST";
  });
  await page.getByRole("button", { name: "Store preference" }).click();
  expect((await saveResponse).ok()).toBeTruthy();

  await expect(input).toHaveValue("");
  await expect(page.getByText("Stored preferences")).toBeVisible();

  expectNoRuntimeIssues(tracker);
});

test("memory drill-down preserves entity state and project back-links", async ({ page }) => {
  const tracker = trackRuntimeIssues(page);

  await page.goto("/personal-data?project=eoq&entity=recent-2", { waitUntil: "domcontentloaded" });
  await expect(page.locator("main h1")).toContainText("Personal Data");

  await expect(page).toHaveURL(/project=eoq/);
  await expect(page).toHaveURL(/entity=recent-2/);
  await expect(page.getByRole("link", { name: "Open project" })).toBeVisible();

  await page.getByRole("link", { name: "Open project" }).click();
  await expect(page).toHaveURL(/\/workplanner\?project=eoq$/);
  await expect(page.getByRole("heading", { name: "Work Planner" })).toBeVisible();

  await page.goBack();
  await expect(page).toHaveURL(/\/personal-data\?/);
  await expect(page).toHaveURL(/project=eoq/);
  await expect(page).toHaveURL(/entity=recent-2/);
  await expect(page.getByRole("link", { name: "Open project" })).toBeVisible();

  expectNoRuntimeIssues(tracker);
});

test("monitoring drawer preserves node and panel state through cross-links", async ({ page }) => {
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/monitoring", "Monitoring");

  await page.locator("main").getByRole("button", { name: "DEV" }).click();
  await expect(page).toHaveURL(/node=dev/);

  await page.locator("main").getByRole("button", { name: "Grafana" }).click();
  await expect(page).toHaveURL(/panel=grafana/);
  await expect(page.getByRole("dialog", { name: "Grafana" })).toBeVisible();

  await page.getByRole("link", { name: "Open services" }).click();
  await expect(page).toHaveURL(/\/services\?node=dev$/);
  await expect(page.locator("main h1")).toContainText("Services");

  await page.goBack();
  await expect(page).toHaveURL(/\/monitoring\?/);
  await expect(page).toHaveURL(/node=dev/);
  await expect(page).toHaveURL(/panel=grafana/);
  await expect(page.getByRole("dialog", { name: "Grafana" })).toBeVisible();

  expectNoRuntimeIssues(tracker);
});

test("media drawer previews external tools and restores route state", async ({ page }) => {
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/media", "Media");

  await page.getByRole("button", { name: "Preview" }).first().click();
  await expect(page).toHaveURL(/panel=plex/);
  await expect(page.getByRole("dialog", { name: "Plex" })).toBeVisible();

  await page.getByRole("link", { name: "Open monitoring" }).click();
  await expect(page).toHaveURL(/\/monitoring$/);
  await expect(page.getByRole("heading", { name: "Monitoring" })).toBeVisible();

  await page.goBack();
  await expect(page).toHaveURL(/\/media\?panel=plex$/);
  await expect(page.getByRole("dialog", { name: "Plex" })).toBeVisible();

  expectNoRuntimeIssues(tracker);
});

test("gallery drawer keeps source filters and output back-links intact", async ({ page }) => {
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/gallery", "Gallery");

  await page.locator("main").getByRole("button", { name: "EoBQ/character" }).first().click();
  await expect(page).toHaveURL(/source=EoBQ%2Fcharacter/);

  await page
    .getByRole("button", {
      name: /Cinematic portrait of a regal queen in dark armor/i,
    })
    .click();
  await expect(page).toHaveURL(/selection=gallery-1/);
  await expect(page.getByRole("dialog", { name: /EoBQ\/character/i })).toBeVisible();

  await page.getByRole("link", { name: "Open outputs" }).click();
  await expect(page).toHaveURL(/\/outputs\?project=eoq$/);
  await expect(page.locator("main h1")).toContainText(/Outputs/i);

  await page.goBack();
  await expect(page).toHaveURL(/\/gallery\?/);
  await expect(page).toHaveURL(/source=EoBQ%2Fcharacter/);
  await expect(page).toHaveURL(/selection=gallery-1/);
  await expect(page.getByRole("dialog", { name: /EoBQ\/character/i })).toBeVisible();

  expectNoRuntimeIssues(tracker);
});

test("home drawer uses monitoring back-links without losing panel state", async ({ page }) => {
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/home", "Home");

  await page.getByRole("button", { name: /Lights/i }).click();
  await expect(page).toHaveURL(/panel=lights/);
  await expect(page.getByRole("dialog", { name: "Lights" })).toBeVisible();

  await page.getByRole("link", { name: "Open monitoring" }).click();
  await expect(page).toHaveURL(/\/monitoring$/);
  await expect(page.getByRole("heading", { name: "Monitoring" })).toBeVisible();

  await page.goBack();
  await expect(page).toHaveURL(/\/home\?panel=lights$/);
  await expect(page.getByRole("dialog", { name: "Lights" })).toBeVisible();

  expectNoRuntimeIssues(tracker);
});
