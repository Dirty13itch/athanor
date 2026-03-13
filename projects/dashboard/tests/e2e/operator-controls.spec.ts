import { expect, test } from "@playwright/test";
import { expectNoRuntimeIssues, gotoRoute, resetBrowserState, trackRuntimeIssues } from "./helpers";

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

test("governor controls persist fixture posture across command-center actions", async ({ page }) => {
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/", "Command Center");

  await expect(page.getByText("current tier production")).toBeVisible();

  await page.getByRole("button", { name: "Pause all automation" }).click();
  await expect(page.getByRole("button", { name: "Resume all automation" })).toBeVisible();

  await page.getByRole("button", { name: "Phone only" }).click();
  await expect(page.getByText("notifications quiet digest")).toBeVisible();
  await expect(page.getByText("approvals summary approval only")).toBeVisible();

  await page.getByRole("button", { name: "Shadow" }).click();
  await expect(page.getByText("current tier shadow")).toBeVisible();

  await expect(page.getByText("Operations readiness")).toBeVisible();
  await expect(page.getByText("Pause and resume automation")).toBeVisible();
  await expect(page.getByText("tests/e2e/operator-controls.spec.ts").first()).toBeVisible();

  await page.getByRole("button", { name: "Resume all automation" }).click();
  await expect(page.getByRole("button", { name: "Pause all automation" })).toBeVisible();

  expectNoRuntimeIssues(tracker);
});
