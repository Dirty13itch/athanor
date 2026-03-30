import { expect, test, type APIResponse } from "@playwright/test";
import { resetBrowserState } from "./helpers";

function operatorSessionConfigured() {
  return Boolean(process.env.PLAYWRIGHT_OPERATOR_TOKEN?.trim());
}

function operatorHeaders() {
  const headers: Record<string, string> = {
    origin: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3905",
  };
  const token = process.env.PLAYWRIGHT_OPERATOR_TOKEN?.trim();
  if (token) {
    headers["x-athanor-operator-token"] = token;
  }
  return headers;
}

async function expectPrivilegedMutation(
  response: APIResponse,
  expected: Record<string, unknown>
) {
  if (operatorSessionConfigured()) {
    expect(response.ok()).toBeTruthy();
    await expect(response.json()).resolves.toMatchObject(expected);
    return;
  }

  expect(response.status()).toBe(403);
  await expect(response.json()).resolves.toMatchObject({
    gate: "athanor-operator-session",
  });
}

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

test("smoke: dashboard mutation endpoints accept operator actions in fixture mode", async ({
  page,
}) => {
  const request = page.context().request;
  const createTask = await request.post("/api/workforce/tasks", {
    headers: operatorHeaders(),
    data: {
      agent: "research-agent",
      prompt: "Summarize the current EoBQ risk posture.",
      priority: "high",
      metadata: { project: "eoq" },
    },
  });
  await expectPrivilegedMutation(createTask, { ok: true, fixture: true, method: "POST" });

  const approveTask = await request.post("/api/workforce/tasks/task-fixture-1/approve", {
    headers: operatorHeaders(),
  });
  await expectPrivilegedMutation(approveTask, { approved: true, fixture: true });

  const cancelTask = await request.post("/api/workforce/tasks/task-fixture-1/cancel", {
    headers: operatorHeaders(),
  });
  await expectPrivilegedMutation(cancelTask, { canceled: true, fixture: true });

  const createGoal = await request.post("/api/workforce/goals", {
    headers: operatorHeaders(),
    data: { text: "Keep EoBQ first-class in the active roadmap.", agent: "global", priority: "high" },
  });
  await expectPrivilegedMutation(createGoal, { ok: true, fixture: true, method: "POST" });

  const deleteGoal = await request.delete("/api/workforce/goals/goal-fixture-1", {
    headers: operatorHeaders(),
  });
  await expectPrivilegedMutation(deleteGoal, { ok: true, fixture: true, method: "DELETE" });

  const resolveNotification = await request.post("/api/workforce/notifications/notification-fixture-1/resolve", {
    headers: operatorHeaders(),
    data: { approved: true },
  });
  await expectPrivilegedMutation(resolveNotification, { resolved: true, fixture: true });

  const generatePlan = await request.post("/api/workforce/plan", {
    headers: operatorHeaders(),
    data: { focus: "command center, tenants, and live operator workflows" },
  });
  await expectPrivilegedMutation(generatePlan, { ok: true, fixture: true, method: "POST" });

  const redirectPlan = await request.post("/api/workforce/redirect", {
    headers: operatorHeaders(),
    data: { direction: "shift attention to review and outputs" },
  });
  await expectPrivilegedMutation(redirectPlan, { ok: true, fixture: true, method: "POST" });

  const runInsights = await request.post("/api/insights/run", {
    headers: operatorHeaders(),
  });
  await expectPrivilegedMutation(runInsights, { ok: true, fixture: true, queued: true });

  const runBenchmarks = await request.post("/api/learning/benchmarks", {
    headers: operatorHeaders(),
  });
  await expectPrivilegedMutation(runBenchmarks, { ok: true, fixture: true, queued: true });

  const preference = await request.post("/api/preferences", {
    headers: operatorHeaders(),
    data: {
      agent: "creative-agent",
      signal_type: "remember_this",
      content: "EoBQ is the featured tenant in audit mode.",
      category: "projects",
    },
  });
  await expectPrivilegedMutation(preference, { ok: true, fixture: true, saved: true });

  const feedback = await request.post("/api/feedback", {
    headers: operatorHeaders(),
    data: { kind: "thumbs_up", subject: "dashboard", detail: "fixture feedback" },
  });
  await expectPrivilegedMutation(feedback, { ok: true, fixture: true, method: "POST" });

  const implicitFeedback = await request.post("/api/feedback/implicit", {
    headers: operatorHeaders(),
    data: {
      session_id: "fixture-session",
      events: [{ type: "route_view", page: "/services", timestamp: Date.now() }],
    },
  });
  await expectPrivilegedMutation(implicitFeedback, {
    stored: expect.any(Number),
  });
});

test("smoke: pipeline mutation endpoints accept operator actions in fixture mode", async ({
  page,
}) => {
  const request = page.context().request;
  const cycle = await request.post("/api/pipeline/cycle", {
    headers: operatorHeaders(),
  });
  await expectPrivilegedMutation(cycle, {
    ok: true,
    fixture: true,
    path: "/v1/pipeline/cycle",
    method: "POST",
  });

  const preview = await request.post("/api/pipeline/preview", {
    headers: operatorHeaders(),
    data: { proposal_id: "preview-0" },
  });
  await expectPrivilegedMutation(preview, {
    ok: true,
    fixture: true,
    path: "/v1/pipeline/preview/approve",
    method: "POST",
  });

  const react = await request.post("/api/pipeline/react", {
    headers: operatorHeaders(),
    data: {
      intent_id: "preview-0",
      reaction: "more",
      intent_metadata: {
        project: "athanor",
        domain: "athanor",
        twelve_word: "Deepen provider evidence for configured-unused lanes before policy promotion.",
      },
    },
  });
  await expectPrivilegedMutation(react, {
    ok: true,
    fixture: true,
    path: "/v1/react",
    method: "POST",
  });

  const boost = await request.post("/api/pipeline/boost", {
    headers: operatorHeaders(),
    data: { domain: "provider-routing", amount: 0.15 },
  });
  await expectPrivilegedMutation(boost, {
    ok: true,
    fixture: true,
    path: "/v1/steer/boost",
    method: "POST",
  });

  const suppress = await request.post("/api/pipeline/suppress", {
    headers: operatorHeaders(),
    data: { domain: "stale-doc-prune", duration_hours: 24 },
  });
  await expectPrivilegedMutation(suppress, {
    ok: true,
    fixture: true,
    path: "/v1/steer/suppress",
    method: "POST",
  });

  const approvePlan = await request.post("/api/pipeline/plans/plan-fixture-1/approve", {
    headers: operatorHeaders(),
  });
  await expectPrivilegedMutation(approvePlan, {
    ok: true,
    fixture: true,
    path: "/v1/plans/plan-fixture-1/approve",
    method: "POST",
  });

  const rejectPlan = await request.post("/api/pipeline/plans/plan-fixture-1/reject", {
    headers: operatorHeaders(),
  });
  await expectPrivilegedMutation(rejectPlan, {
    ok: true,
    fixture: true,
    path: "/v1/plans/plan-fixture-1/reject",
    method: "POST",
  });
});

test("smoke: browser-adjacent rich action endpoints are safe in fixture mode", async ({
  page,
}) => {
  const request = page.context().request;
  const subscribe = await request.post("/api/push/subscribe", {
    data: {
      endpoint: "https://push.example.test/subscription",
      keys: {
        p256dh: "fixture-p256dh",
        auth: "fixture-auth",
      },
    },
  });
  expect(subscribe.ok()).toBeTruthy();
  await expect(subscribe.json()).resolves.toMatchObject({ ok: true, count: 1 });

  const sendPush = await request.post("/api/push/send", {
    headers: operatorHeaders(),
    data: { title: "Athanor", body: "Fixture push validation", url: "/notifications" },
  });
  if (operatorSessionConfigured()) {
    expect(sendPush.ok()).toBeTruthy();
    await expect(sendPush.json()).resolves.toMatchObject({
      fixture: true,
      failed: 0,
      sent: expect.any(Number),
      total: expect.any(Number),
    });
  } else {
    await expectPrivilegedMutation(sendPush, { gate: "athanor-operator-session" });
  }

  const deletePush = await request.delete("/api/push/subscribe", {
    data: { endpoint: "https://push.example.test/subscription" },
  });
  expect(deletePush.ok()).toBeTruthy();
  await expect(deletePush.json()).resolves.toMatchObject({ ok: true });

  const ttsValidation = await request.post("/api/tts", {
    data: { input: "" },
  });
  expect(ttsValidation.status()).toBe(400);

  const tts = await request.fetch("/api/tts", {
    method: "POST",
    data: { input: "Athanor fixture voice check.", voice: "alloy", speed: 1.1 },
  });
  expect(tts.ok()).toBeTruthy();
  expect(tts.headers()["content-type"]).toContain("audio/mpeg");
  expect(tts.headers()["x-athanor-fixture"]).toBe("1");

  const comfyGenerate = await request.post("/api/comfyui/generate", {
    data: { workflow: "character", prompt: "Fixture queen portrait", seed: 1234 },
  });
  expect(comfyGenerate.ok()).toBeTruthy();
  await expect(comfyGenerate.json()).resolves.toMatchObject({
    prompt_id: "fixture-comfyui-prompt",
    queued: true,
  });

  const comfyHistory = await request.get("/api/comfyui/history?max_items=5");
  expect(comfyHistory.ok()).toBeTruthy();
  await expect(comfyHistory.json()).resolves.toMatchObject({ items: expect.any(Array) });

  const comfyQueue = await request.get("/api/comfyui/queue");
  expect(comfyQueue.ok()).toBeTruthy();
  await expect(comfyQueue.json()).resolves.toMatchObject({
    queue_running: expect.any(Array),
    queue_pending: expect.any(Array),
  });

  const comfyStats = await request.get("/api/comfyui/stats");
  expect(comfyStats.ok()).toBeTruthy();
  await expect(comfyStats.json()).resolves.toMatchObject({
    system: expect.any(Object),
    devices: expect.any(Array),
  });

  const serviceWorker = await request.get("/sw.js");
  expect(serviceWorker.ok()).toBeTruthy();
  expect(serviceWorker.headers()["content-type"]).toContain("javascript");
});
