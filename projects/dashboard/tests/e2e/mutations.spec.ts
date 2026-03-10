import { expect, test } from "@playwright/test";

test("smoke: dashboard mutation endpoints accept operator actions in fixture mode", async ({
  request,
}) => {
  const createTask = await request.post("/api/workforce/tasks", {
    data: {
      agent: "research-agent",
      prompt: "Summarize the current EoBQ risk posture.",
      priority: "high",
      metadata: { project: "eoq" },
    },
  });
  expect(createTask.ok()).toBeTruthy();
  await expect(createTask.json()).resolves.toMatchObject({ ok: true, fixture: true, method: "POST" });

  const approveTask = await request.post("/api/workforce/tasks/task-fixture-1/approve");
  expect(approveTask.ok()).toBeTruthy();
  await expect(approveTask.json()).resolves.toMatchObject({ approved: true, fixture: true });

  const cancelTask = await request.post("/api/workforce/tasks/task-fixture-1/cancel");
  expect(cancelTask.ok()).toBeTruthy();
  await expect(cancelTask.json()).resolves.toMatchObject({ canceled: true, fixture: true });

  const createGoal = await request.post("/api/workforce/goals", {
    data: { text: "Keep EoBQ first-class in the active roadmap.", agent: "global", priority: "high" },
  });
  expect(createGoal.ok()).toBeTruthy();
  await expect(createGoal.json()).resolves.toMatchObject({ ok: true, fixture: true, method: "POST" });

  const deleteGoal = await request.delete("/api/workforce/goals/goal-fixture-1");
  expect(deleteGoal.ok()).toBeTruthy();
  await expect(deleteGoal.json()).resolves.toMatchObject({ ok: true, fixture: true, method: "DELETE" });

  const resolveNotification = await request.post("/api/workforce/notifications/notification-fixture-1/resolve", {
    data: { approved: true },
  });
  expect(resolveNotification.ok()).toBeTruthy();
  await expect(resolveNotification.json()).resolves.toMatchObject({ resolved: true, fixture: true });

  const generatePlan = await request.post("/api/workforce/plan", {
    data: { focus: "command center, tenants, and live operator workflows" },
  });
  expect(generatePlan.ok()).toBeTruthy();
  await expect(generatePlan.json()).resolves.toMatchObject({ ok: true, fixture: true, method: "POST" });

  const redirectPlan = await request.post("/api/workforce/redirect", {
    data: { direction: "shift attention to review and outputs" },
  });
  expect(redirectPlan.ok()).toBeTruthy();
  await expect(redirectPlan.json()).resolves.toMatchObject({ ok: true, fixture: true, method: "POST" });

  const runInsights = await request.post("/api/insights/run");
  expect(runInsights.ok()).toBeTruthy();
  await expect(runInsights.json()).resolves.toMatchObject({ ok: true, fixture: true, queued: true });

  const runBenchmarks = await request.post("/api/learning/benchmarks");
  expect(runBenchmarks.ok()).toBeTruthy();
  await expect(runBenchmarks.json()).resolves.toMatchObject({ ok: true, fixture: true, queued: true });

  const preference = await request.post("/api/preferences", {
    data: {
      agent: "creative-agent",
      signal_type: "remember_this",
      content: "EoBQ is the featured tenant in audit mode.",
      category: "projects",
    },
  });
  expect(preference.ok()).toBeTruthy();
  await expect(preference.json()).resolves.toMatchObject({ ok: true, fixture: true, saved: true });

  const feedback = await request.post("/api/feedback", {
    data: { kind: "thumbs_up", subject: "dashboard", detail: "fixture feedback" },
  });
  expect(feedback.ok()).toBeTruthy();
  await expect(feedback.json()).resolves.toMatchObject({ ok: true, fixture: true, method: "POST" });

  const implicitFeedback = await request.post("/api/feedback/implicit", {
    data: {
      session_id: "fixture-session",
      events: [{ type: "route_view", page: "/services", timestamp: Date.now() }],
    },
  });
  expect(implicitFeedback.ok()).toBeTruthy();
  await expect(implicitFeedback.json()).resolves.toMatchObject({
    stored: expect.any(Number),
  });
});

test("smoke: browser-adjacent rich action endpoints are safe in fixture mode", async ({
  request,
}) => {
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
    data: { title: "Athanor", body: "Fixture push validation", url: "/notifications" },
  });
  expect(sendPush.ok()).toBeTruthy();
  await expect(sendPush.json()).resolves.toMatchObject({ fixture: true, sent: 1, failed: 0, total: 1 });

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
