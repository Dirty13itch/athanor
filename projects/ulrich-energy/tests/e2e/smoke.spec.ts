import { expect, test } from "@playwright/test";

const ROUTES = [
  "/",
  "/analytics",
  "/clients",
  "/inspections",
  "/inspections/new",
  "/projects",
  "/reports",
];

test("routes render without runtime errors", async ({ page }) => {
  for (const route of ROUTES) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    await expect(page.locator("h1")).toBeVisible();
  }
});

test("api smoke covers analytics, clients, inspections, projects, and reports", async ({ request }) => {
  const analytics = await request.get("/api/analytics/dashboard");
  expect(analytics.ok()).toBeTruthy();
  await expect(analytics.json()).resolves.toMatchObject({ data: expect.any(Object) });

  const clients = await request.get("/api/clients");
  expect(clients.ok()).toBeTruthy();
  await expect(clients.json()).resolves.toMatchObject({ data: expect.any(Array) });

  const inspections = await request.get("/api/inspections");
  expect(inspections.ok()).toBeTruthy();
  const inspectionPayload = await inspections.json();
  expect(Array.isArray(inspectionPayload.inspections)).toBeTruthy();
  const firstInspectionId = inspectionPayload.inspections[0]?.id;
  expect(firstInspectionId).toBeTruthy();

  const inspectionDetail = await request.get(`/api/inspections/${firstInspectionId}`);
  expect(inspectionDetail.ok()).toBeTruthy();

  const projects = await request.get("/api/projects");
  expect(projects.ok()).toBeTruthy();
  await expect(projects.json()).resolves.toMatchObject({ projects: expect.any(Array) });

  const reports = await request.get("/api/reports");
  expect(reports.ok()).toBeTruthy();
  const reportPayload = await reports.json();
  expect(Array.isArray(reportPayload.reports)).toBeTruthy();

  const generate = await request.post("/api/reports/generate", {
    data: { inspectionId: firstInspectionId },
  });
  expect(generate.ok()).toBeTruthy();
  const generatePayload = await generate.json();
  expect(generatePayload.report?.id).toBeTruthy();

  const reportDetail = await request.get(`/api/reports/${generatePayload.report.id}`);
  expect(reportDetail.ok()).toBeTruthy();
});
