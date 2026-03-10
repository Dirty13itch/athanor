import { expect, test, type APIResponse } from "@playwright/test";

async function expectJsonKeys(response: APIResponse, keys: string[]) {
  const json = await response.json();
  for (const key of keys) {
    expect(json).toHaveProperty(key);
  }
  return json;
}

test("smoke: overview snapshot endpoint returns the expected shape", async ({ request }) => {
  const response = await request.get("/api/overview");
  expect(response.ok()).toBeTruthy();

  const json = await expectJsonKeys(response, [
    "generatedAt",
    "summary",
    "nodes",
    "services",
    "backends",
    "agents",
    "projects",
    "alerts",
    "workforce",
  ]);

  expect(Array.isArray(json.nodes)).toBeTruthy();
  expect(Array.isArray(json.services)).toBeTruthy();
  expect(Array.isArray(json.projects)).toBeTruthy();
});

test("smoke: services endpoints return snapshots and history", async ({ request }) => {
  const snapshotResponse = await request.get("/api/services");
  expect(snapshotResponse.ok()).toBeTruthy();
  const snapshot = await expectJsonKeys(snapshotResponse, [
    "generatedAt",
    "summary",
    "nodes",
    "services",
  ]);

  expect(Array.isArray(snapshot.nodes)).toBeTruthy();
  expect(Array.isArray(snapshot.services)).toBeTruthy();

  const historyResponse = await request.get("/api/services/history?window=6h");
  expect(historyResponse.ok()).toBeTruthy();
  const history = await expectJsonKeys(historyResponse, [
    "generatedAt",
    "window",
    "aggregate",
    "series",
  ]);

  expect(Array.isArray(history.aggregate)).toBeTruthy();
  expect(Array.isArray(history.series)).toBeTruthy();
});

test("smoke: gpu endpoints return snapshots and history", async ({ request }) => {
  const snapshotResponse = await request.get("/api/gpu");
  expect(snapshotResponse.ok()).toBeTruthy();
  const snapshot = await expectJsonKeys(snapshotResponse, [
    "generatedAt",
    "summary",
    "nodes",
    "gpus",
  ]);

  expect(Array.isArray(snapshot.nodes)).toBeTruthy();
  expect(Array.isArray(snapshot.gpus)).toBeTruthy();

  const historyResponse = await request.get("/api/gpu/history?window=6h");
  expect(historyResponse.ok()).toBeTruthy();
  const history = await expectJsonKeys(historyResponse, [
    "generatedAt",
    "window",
    "nodes",
    "gpus",
  ]);

  expect(Array.isArray(history.nodes)).toBeTruthy();
  expect(Array.isArray(history.gpus)).toBeTruthy();
});

test("smoke: operator catalog endpoints return inventories", async ({ request }) => {
  const modelsResponse = await request.get("/api/models");
  expect(modelsResponse.ok()).toBeTruthy();
  const models = await expectJsonKeys(modelsResponse, ["generatedAt", "backends", "models"]);
  expect(Array.isArray(models.backends)).toBeTruthy();
  expect(Array.isArray(models.models)).toBeTruthy();

  const agentsResponse = await request.get("/api/agents");
  expect(agentsResponse.ok()).toBeTruthy();
  const agents = await expectJsonKeys(agentsResponse, ["generatedAt", "agents"]);
  expect(Array.isArray(agents.agents)).toBeTruthy();

  const projectsResponse = await request.get("/api/projects");
  expect(projectsResponse.ok()).toBeTruthy();
  const projects = await expectJsonKeys(projectsResponse, ["generatedAt", "projects"]);
  expect(Array.isArray(projects.projects)).toBeTruthy();
});

test("smoke: workforce snapshot endpoint returns the expected sections", async ({ request }) => {
  const response = await request.get("/api/workforce");
  expect(response.ok()).toBeTruthy();

  const json = await expectJsonKeys(response, [
    "generatedAt",
    "summary",
    "workplan",
    "tasks",
    "goals",
    "trust",
    "notifications",
    "workspace",
    "subscriptions",
    "conventions",
    "improvement",
    "agents",
    "projects",
    "schedules",
  ]);

  expect(Array.isArray(json.tasks)).toBeTruthy();
  expect(Array.isArray(json.goals)).toBeTruthy();
  expect(Array.isArray(json.notifications)).toBeTruthy();
  expect(Array.isArray(json.projects)).toBeTruthy();
});

test("smoke: family snapshot endpoints return the expected shape", async ({ request }) => {
  const historyResponse = await request.get("/api/history");
  expect(historyResponse.ok()).toBeTruthy();
  const history = await expectJsonKeys(historyResponse, [
    "generatedAt",
    "summary",
    "projects",
    "agents",
    "tasks",
    "activity",
    "conversations",
    "outputs",
  ]);
  expect(Array.isArray(history.activity)).toBeTruthy();
  expect(Array.isArray(history.conversations)).toBeTruthy();
  expect(Array.isArray(history.outputs)).toBeTruthy();

  const intelligenceResponse = await request.get("/api/intelligence");
  expect(intelligenceResponse.ok()).toBeTruthy();
  const intelligence = await expectJsonKeys(intelligenceResponse, [
    "generatedAt",
    "projects",
    "agents",
    "report",
    "learning",
    "improvement",
    "reviewTasks",
  ]);
  expect(Array.isArray(intelligence.reviewTasks)).toBeTruthy();

  const memoryResponse = await request.get("/api/memory");
  expect(memoryResponse.ok()).toBeTruthy();
  const memory = await expectJsonKeys(memoryResponse, [
    "generatedAt",
    "projects",
    "summary",
    "preferences",
    "recentItems",
    "categories",
    "topTopics",
    "graphLabels",
  ]);
  expect(Array.isArray(memory.preferences)).toBeTruthy();
  expect(Array.isArray(memory.recentItems)).toBeTruthy();
});

test("smoke: domain snapshot endpoints return the expected shape", async ({ request }) => {
  const monitoringResponse = await request.get("/api/monitoring");
  expect(monitoringResponse.ok()).toBeTruthy();
  const monitoring = await expectJsonKeys(monitoringResponse, [
    "generatedAt",
    "summary",
    "nodes",
    "dashboards",
  ]);
  expect(Array.isArray(monitoring.nodes)).toBeTruthy();
  expect(Array.isArray(monitoring.dashboards)).toBeTruthy();

  const mediaResponse = await request.get("/api/media/overview");
  expect(mediaResponse.ok()).toBeTruthy();
  const media = await expectJsonKeys(mediaResponse, [
    "generatedAt",
    "streamCount",
    "sessions",
    "downloads",
    "tvUpcoming",
    "movieUpcoming",
    "watchHistory",
    "launchLinks",
  ]);
  expect(Array.isArray(media.sessions)).toBeTruthy();
  expect(Array.isArray(media.launchLinks)).toBeTruthy();

  const galleryResponse = await request.get("/api/gallery/overview");
  expect(galleryResponse.ok()).toBeTruthy();
  const gallery = await expectJsonKeys(galleryResponse, [
    "generatedAt",
    "queueRunning",
    "queuePending",
    "items",
  ]);
  expect(Array.isArray(gallery.items)).toBeTruthy();

  const homeResponse = await request.get("/api/home/overview");
  expect(homeResponse.ok()).toBeTruthy();
  const home = await expectJsonKeys(homeResponse, [
    "generatedAt",
    "online",
    "configured",
    "summary",
    "setupSteps",
    "panels",
  ]);
  expect(Array.isArray(home.setupSteps)).toBeTruthy();
  expect(Array.isArray(home.panels)).toBeTruthy();
});
