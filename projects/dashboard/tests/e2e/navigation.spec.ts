import { expect, test } from "@playwright/test";
import { gotoRoute, resetBrowserState } from "./helpers";

async function navigateFromShell(
  page: import("@playwright/test").Page,
  label: string,
  destination: RegExp,
  heading: string
) {
  const mobileNavButton = page.getByRole("button", { name: "Open navigation" });
  if (await mobileNavButton.isVisible()) {
    await mobileNavButton.click();
  }

  await page.getByRole("link", { name: label }).click();
  await expect(page).toHaveURL(destination);
  await expect(page.locator("main h1")).toContainText(heading);
}

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

test("navigates core routes from the shell", async ({ page }) => {
  await gotoRoute(page, "/", "Command Center");

  await navigateFromShell(page, "Services", /\/services$/, "Services");
  await navigateFromShell(page, "GPU Metrics", /\/gpu$/, "GPU Metrics");
  await navigateFromShell(page, "Direct Chat", /\/chat$/, "Direct Chat");
});

test("opens the command palette and routes to incidents", async ({ page }) => {
  await gotoRoute(page, "/", "Command Center");

  const paletteButton = page.getByRole("button", { name: /command palette|open command palette/i });
  await paletteButton.first().click();
  await expect(page.getByRole("dialog", { name: "Command palette" })).toBeAttached();

  await page.getByPlaceholder("Jump to a route, tool, or priority item").fill("services");
  await page.keyboard.press("Enter");

  await expect(page).toHaveURL(/\/services$/);
  await expect(page.getByRole("heading", { name: "Services" })).toBeVisible();
});
