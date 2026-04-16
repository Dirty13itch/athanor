import { expect, test } from "@playwright/test";
import {
  gotoRoute,
  installClipboardMock,
  installExportCapture,
  mockChatStream,
  readClipboardText,
  resetBrowserState,
  waitForCapturedExport,
} from "./helpers";

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
  await installClipboardMock(page);
  await installExportCapture(page);
});

test("copies and exports a direct-chat session", async ({ page }) => {
  await mockChatStream(page, [
    {
      type: "assistant_delta",
      timestamp: "2026-03-10T12:00:01.000Z",
      content: "Cluster posture is stable. ",
    },
    {
      type: "assistant_delta",
      timestamp: "2026-03-10T12:00:02.000Z",
      content: "EoBQ remains the featured tenant.",
    },
    {
      type: "done",
      timestamp: "2026-03-10T12:00:03.000Z",
      finishReason: "stop",
    },
  ]);

  await gotoRoute(page, "/chat", "Direct Chat");

  await page.getByPlaceholder(/Message /i).fill("Summarize current priorities.");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("Cluster posture is stable. EoBQ remains the featured tenant.")).toBeVisible();

  await page.getByRole("button", { name: "Copy" }).click();
  await expect
    .poll(() => readClipboardText(page))
    .toContain("USER: Summarize current priorities.");
  await expect
    .poll(() => readClipboardText(page))
    .toContain("ASSISTANT: Cluster posture is stable. EoBQ remains the featured tenant.");

  const exportedSession = waitForCapturedExport(page);
  await page.getByRole("button", { name: "Export session" }).click();
  const sessionFile = JSON.parse((await exportedSession).text);

  expect(sessionFile).toMatchObject({
    title: "Summarize current priorities.",
    messages: [
      { role: "user", content: "Summarize current priorities." },
      { role: "assistant", content: "Cluster posture is stable. EoBQ remains the featured tenant." },
    ],
  });
});

test("copies and exports an agent thread", async ({ page }) => {
  await mockChatStream(page, [
    {
      type: "tool_start",
      timestamp: "2026-03-10T12:02:00.000Z",
      toolCallId: "tool-copy-export",
      name: "cluster_health",
      args: { scope: "services" },
    },
    {
      type: "tool_end",
      timestamp: "2026-03-10T12:02:01.000Z",
      toolCallId: "tool-copy-export",
      name: "cluster_health",
      output: "LiteLLM and the workshop worker are healthy.",
      durationMs: 512,
    },
    {
      type: "assistant_delta",
      timestamp: "2026-03-10T12:02:02.000Z",
      content: "I checked the stack. LiteLLM and the workshop worker are healthy.",
    },
    {
      type: "done",
      timestamp: "2026-03-10T12:02:03.000Z",
      finishReason: "stop",
    },
  ]);

  await gotoRoute(page, "/agents", "Agent Console");

  await page
    .getByPlaceholder(/Message General Assistant/i)
    .fill("Check the live inference stack.");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(
    page.getByText("I checked the stack. LiteLLM and the workshop worker are healthy.")
  ).toBeVisible();

  await page.getByRole("button", { name: "Copy" }).click();
  await expect
    .poll(() => readClipboardText(page))
    .toContain("USER: Check the live inference stack.");
  await expect
    .poll(() => readClipboardText(page))
    .toContain("ASSISTANT: I checked the stack. LiteLLM and the workshop worker are healthy.");

  const exportedThread = waitForCapturedExport(page);
  await page.getByRole("button", { name: "Export thread" }).click();
  const threadFile = JSON.parse((await exportedThread).text);

  expect(threadFile).toMatchObject({
    agentId: "general-assistant",
    messages: [
      { role: "user", content: "Check the live inference stack." },
      {
        role: "assistant",
        content: "I checked the stack. LiteLLM and the workshop worker are healthy.",
      },
    ],
  });
});

test("copies service endpoints and exports the filtered services view", async ({ page }) => {
  await gotoRoute(page, "/services", "Services");

  await page.locator("main button").filter({ hasText: "Export view" }).first().click();
  const servicesFile = JSON.parse((await waitForCapturedExport(page)).text);

  expect(servicesFile).toMatchObject({
    summary: { total: expect.any(Number) },
    services: expect.any(Array),
  });

  await page.locator("button").filter({ hasText: "LiteLLM Proxy" }).first().click();
  await expect(page.getByRole("heading", { name: "LiteLLM Proxy" })).toBeVisible();

  await page.getByRole("button", { name: "Copy endpoint" }).click();
  await expect
    .poll(() => readClipboardText(page))
    .toContain("http");
});
