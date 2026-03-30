import { expect, test } from "@playwright/test";
import { expectNoRuntimeIssues, gotoRoute, resetBrowserState, trackRuntimeIssues } from "./helpers";

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

async function clickGovernorAction(button: import("@playwright/test").Locator) {
  await button.click();
}

test("governor controls persist fixture posture across command-center actions", async ({ page }) => {
  const tracker = trackRuntimeIssues(page);

  await gotoRoute(page, "/", "Command Center");
  const governanceSection = page.locator("details").filter({
    has: page.locator("summary").getByText("Governance"),
  });
  await governanceSection.locator("summary").click();

  const governorCard = governanceSection.locator(".surface-panel").filter({
    has: page.getByText("Governor posture"),
  });

  await expect(governorCard.getByText("current tier production")).toBeVisible();

  await clickGovernorAction(
    governorCard.getByRole("button", { name: "Pause all automation" })
  );
  await expect(
    governorCard.getByRole("button", { name: "Resume all automation" })
  ).toBeVisible({ timeout: 20_000 });

  await clickGovernorAction(
    governorCard.getByRole("button", { name: "Phone only" })
  );
  await expect(governorCard.getByText("notifications quiet digest")).toBeVisible({
    timeout: 20_000,
  });
  await expect(governorCard.getByText("approvals summary approval only")).toBeVisible({
    timeout: 20_000,
  });

  await clickGovernorAction(
    governorCard.getByRole("button", { name: "Shadow" })
  );
  await expect(governorCard.getByText("current tier shadow")).toBeVisible({ timeout: 20_000 });

  await expect(page.getByText("Operations readiness")).toBeVisible();
  await expect(page.getByText("Pause and resume automation")).toBeVisible();
  await expect(page.getByText("tests/e2e/operator-controls.spec.ts").first()).toBeVisible();

  await clickGovernorAction(
    governorCard.getByRole("button", { name: "Resume all automation" })
  );
  await expect(governorCard.getByRole("button", { name: "Pause all automation" })).toBeVisible({
    timeout: 20_000,
  });

  expectNoRuntimeIssues(tracker);
});
