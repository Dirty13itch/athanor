import { expect, test } from "@playwright/test";
import { expectNoRuntimeIssues, gotoRoute, resetBrowserState, trackRuntimeIssues } from "./helpers";

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

async function clickGovernorAction(button: import("@playwright/test").Locator) {
  await button.click();
}

test("governor controls persist fixture posture across route changes", async ({ page }) => {
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/governor", "Governor");
  const governorCard = page.locator(".surface-panel").filter({
    hasText: "Governor posture",
  }).first();

  await expect(governorCard.getByText("current tier production")).toBeVisible();

  await clickGovernorAction(
    governorCard.getByRole("button", { name: "Pause all automation" })
  );
  await expect(
    governorCard.getByRole("button", { name: "Resume all automation" })
  ).toBeVisible({ timeout: 20_000 });

  await clickGovernorAction(
    governorCard.getByRole("button", { name: /phone only/i })
  );
  await expect(governorCard.getByText("notifications quiet digest")).toBeVisible({
    timeout: 20_000,
  });
  await expect(governorCard.getByText("approvals summary approval only")).toBeVisible({
    timeout: 20_000,
  });

  await clickGovernorAction(
    governorCard.getByRole("button", { name: /^shadow$/i })
  );
  await expect(governorCard.getByText("current tier shadow")).toBeVisible({ timeout: 20_000 });

  await expect(page.getByText("Control Stack").first()).toBeVisible();
  await expect(page.getByText("Agent Trust Scores").first()).toBeVisible();

  await gotoRoute(page, "/", /Triage the system|Command Center/i);
  await gotoRoute(page, "/governor", "Governor");

  const persistedGovernorCard = page.locator(".surface-panel").filter({
    hasText: "Governor posture",
  }).first();
  await expect(persistedGovernorCard.getByText("current tier shadow")).toBeVisible({
    timeout: 20_000,
  });
  await expect(persistedGovernorCard.getByText("notifications quiet digest")).toBeVisible({
    timeout: 20_000,
  });
  await expect(
    persistedGovernorCard.getByRole("button", { name: "Resume all automation" })
  ).toBeVisible({ timeout: 20_000 });

  await clickGovernorAction(
    persistedGovernorCard.getByRole("button", { name: /^production$/i })
  );
  await expect(persistedGovernorCard.getByText("current tier production")).toBeVisible({
    timeout: 20_000,
  });

  await clickGovernorAction(
    persistedGovernorCard.getByRole("button", { name: /^auto$/i })
  );
  await expect(persistedGovernorCard.getByText(/mode auto/i)).toBeVisible({
    timeout: 20_000,
  });

  await clickGovernorAction(
    persistedGovernorCard.getByRole("button", { name: "Resume all automation" })
  );
  await expect(
    persistedGovernorCard.getByRole("button", { name: "Pause all automation" })
  ).toBeVisible({ timeout: 20_000 });

  expectNoRuntimeIssues(tracker);
});
