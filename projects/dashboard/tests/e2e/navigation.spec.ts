import { expect, test } from "@playwright/test";

test("navigates core routes", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();

  await page.getByRole("link", { name: "Services" }).click();
  await expect(page.getByRole("heading", { name: "Services" })).toBeVisible();

  await page.getByRole("link", { name: "GPU Metrics" }).click();
  await expect(page.getByRole("heading", { name: "GPU Metrics" })).toBeVisible();
});
