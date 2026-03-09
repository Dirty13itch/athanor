import { expect, test } from "@playwright/test";
import { gotoRoute, mockChatStream, resetBrowserState } from "./helpers";

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

test("runs a direct chat session with streamed assistant output", async ({ page }) => {
  await mockChatStream(page, [
    {
      type: "assistant_delta",
      timestamp: "2026-03-09T15:00:01.000Z",
      content: "Athanor is nominal. ",
    },
    {
      type: "assistant_delta",
      timestamp: "2026-03-09T15:00:02.000Z",
      content: "The only active issue is Speaches.",
    },
    {
      type: "done",
      timestamp: "2026-03-09T15:00:03.000Z",
      finishReason: "stop",
    },
  ]);

  await gotoRoute(page, "/chat", "Direct Chat");

  await page.getByPlaceholder(/Message qwen3-32b/i).fill("Summarize the cluster posture.");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(
    page.getByRole("button", { name: /Summarize the cluster posture\.\s+2 messages/i })
  ).toBeVisible();
  await expect(page.getByText("Athanor is nominal. The only active issue is Speaches.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Export session" })).toBeEnabled();
});

test("renders agent tool activity with stable tool-call ids", async ({ page }) => {
  await mockChatStream(page, [
    {
      type: "tool_start",
      timestamp: "2026-03-09T15:01:00.000Z",
      toolCallId: "tool-1",
      name: "cluster_health",
      args: { scope: "services" },
    },
    {
      type: "tool_end",
      timestamp: "2026-03-09T15:01:01.000Z",
      toolCallId: "tool-1",
      name: "cluster_health",
      output: "Speaches is degraded while all other services are healthy.",
      durationMs: 812,
    },
    {
      type: "assistant_delta",
      timestamp: "2026-03-09T15:01:02.000Z",
      content: "I checked the cluster. Speaches is degraded; all other monitored services are healthy.",
    },
    {
      type: "done",
      timestamp: "2026-03-09T15:01:03.000Z",
      finishReason: "stop",
    },
  ]);

  await gotoRoute(page, "/agents", "Agent Console");

  await page
    .getByPlaceholder(/Message General Assistant/i)
    .fill("Check service health and summarize the current state.");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("cluster_health")).toBeVisible();
  await expect(page.getByText("812ms")).toBeVisible();
  await expect(page.getByText(/Speaches is degraded while all other services are healthy/i)).toBeVisible();
  await expect(
    page.getByText(/I checked the cluster. Speaches is degraded; all other monitored services are healthy/i)
  ).toBeVisible();
});
