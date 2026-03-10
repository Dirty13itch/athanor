import { expect, test } from "@playwright/test";
import { seedSavedGame } from "./helpers";

test.beforeEach(async ({ page }) => {
  await seedSavedGame(page);
  await page.goto("/", { waitUntil: "domcontentloaded" });
});

test("supports continue flow and core navigation overlays", async ({ page }) => {
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByRole("heading", { name: "Courtyard" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Log" })).toBeVisible();

  await page.getByRole("button", { name: "Log" }).click();
  await expect(page.getByText(/Dialogue History/i)).toBeVisible();
  await page.getByRole("button", { name: /Close \(H\)/i }).click();
  await expect(page.getByText(/Dialogue History/i)).not.toBeVisible();

  await page.getByRole("button", { name: "Map" }).click();
  await expect(page.getByText(/Map/i)).toBeVisible();
  await page.getByRole("button", { name: /Close \(M\)/i }).click();

  await page.getByRole("button", { name: "Explore" }).click();
  await expect(page.getByText(/Walk to the keep/i)).toBeVisible();
  await page.getByRole("button", { name: /^Close$/ }).first().click();

  await page.getByTitle(/Settings/i).click();
  await expect(page.getByText("Settings")).toBeVisible();
  await page.getByRole("button", { name: /Controls/i }).click();
  await expect(page.getByText(/Space \/ Enter/i)).toBeVisible();
});

test("supports freeform dialogue and choice interactions", async ({ page }) => {
  await page.getByRole("button", { name: "Continue" }).click();

  await page.getByPlaceholder(/Speak to Isolde/i).fill("Tell me the court's weakest seam.");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/Choose whether to press harder/i)).toBeVisible({ timeout: 15_000 });

  const choiceButton = page.getByRole("button").filter({ hasText: /Step closer/i }).first();
  await expect(choiceButton).toBeVisible();
  await choiceButton.click();
  await expect(page.getByText(/Choose whether to press harder/i)).toBeVisible({ timeout: 15_000 });
});

test("supports gallery filters and reference-library persona workflows", async ({ page }) => {
  await page.goto("/gallery", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: /Portrait Gallery/i })).toBeVisible();
  await page.getByRole("button", { name: "Isolde" }).click();
  await expect(page.getByText(/1 image generated|1 images generated/i)).toBeVisible();
  await page.locator("img").first().click();
  await expect(page.getByRole("button", { name: /Close \(Esc\)/i })).toBeVisible();
  await page.keyboard.press("Escape");

  await page.goto("/references", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: /Reference Library/i })).toBeVisible();
  await page.getByRole("button", { name: "Queens" }).click();
  const personaNameInput = page.getByPlaceholder("New Queens persona name...");
  await personaNameInput.pressSequentially("Cassia");
  await expect(personaNameInput).toHaveValue("Cassia");
  await expect(page.getByRole("button", { name: /Add Persona/i })).toBeEnabled();
  await page.getByRole("button", { name: /Add Persona/i }).click();
  await expect(page.getByText("Cassia")).toBeVisible();

  await page.getByRole("button", { name: /\+ Upload Photo/i }).last().click();
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles({
    name: "cassia-reference.png",
    mimeType: "image/png",
    buffer: Buffer.from("fixture"),
  });
  await expect(page.getByText(/cassia-ref/i)).toBeVisible();
});
