import { expect, test } from "@playwright/test";
import { gotoRoute, resetBrowserState } from "./helpers";

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

test("persists service filters in the URL and opens the detail drawer", async ({ page }) => {
  await gotoRoute(page, "/services", "Services");

  await page.locator("button").filter({ hasText: /^Degraded$/ }).first().click();

  await expect(page).toHaveURL(/status=degraded/);

  await page.getByRole("button", { name: /Speaches/i }).click();

  await expect(page).toHaveURL(/service=speaches/);
  await expect(page.getByRole("dialog", { name: /Speaches/i })).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy endpoint" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open Grafana" })).toBeVisible();
});

test("updates GPU time range and compare state from the console", async ({ page }) => {
  await gotoRoute(page, "/gpu", "GPU Metrics");

  await page.getByRole("button", { name: "24h" }).click();
  await expect(page).toHaveURL(/window=24h/);

  await page.getByRole("button", { name: "Pin compare" }).nth(0).click();
  await page.getByRole("button", { name: "Pin compare" }).nth(1).click();

  await expect(page).toHaveURL(/compare=/);
  await expect(page.getByText("Pinned comparison")).toBeVisible();

  await page.getByRole("button", { name: "Focus" }).nth(0).click();
  await expect(page).toHaveURL(/highlight=/);
  await expect(page.getByText("Selected GPU drill-down")).toBeVisible();
});
