import { expect, test } from "@playwright/test";

test("renders direct chat console", async ({ page }) => {
  await page.goto("/chat");
  await expect(page.getByRole("heading", { name: "Direct Chat" })).toBeVisible();
  await expect(page.getByRole("button", { name: "New session" })).toBeVisible();
});

test("renders agent console", async ({ page }) => {
  await page.goto("/agents");
  await expect(page.getByRole("heading", { name: "Agent Console" })).toBeVisible();
  await expect(page.getByRole("button", { name: "New thread" })).toBeVisible();
});
