import { expect, test } from "@playwright/test";

test("creates an inspection and drills into the generated report", async ({ page }) => {
  await page.goto("/inspections/new", { waitUntil: "domcontentloaded" });
  await page.getByLabel("Property Address").fill("4321 Cedar Street, Minneapolis, MN 55408");
  await page.getByLabel("Builder").fill("Ulrich Fixture Homes");
  await page.getByLabel("Inspector").fill("Shaun");
  await page.getByRole("button", { name: /Create Inspection/i }).click();

  await expect(page).toHaveURL(/\/inspections\//);
  await expect(page.getByRole("heading", { name: /Inspection Detail/i })).toBeVisible();
  await expect(page.getByText(/4321 Cedar Street/i)).toBeVisible();

  await page.getByRole("button", { name: /Generate Report/i }).click();
  await expect(page).toHaveURL(/\/reports\//);
  await expect(page.getByRole("heading", { name: /Report Detail/i })).toBeVisible();
  await expect(page.getByText(/Fixture narrative/i)).toBeVisible();
});

test("supports dashboard quick actions and report drill-down", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: /Ulrich Energy/i })).toBeVisible();

  await page.getByRole("link", { name: /View Reports/i }).click();
  await expect(page).toHaveURL(/\/reports$/);
  await page.getByRole("link").filter({ hasText: /5678 Elm Ave/i }).first().click();
  await expect(page).toHaveURL(/\/reports\//);
  await page.getByRole("link", { name: /Open Inspection/i }).click();
  await expect(page).toHaveURL(/\/inspections\//);
});
