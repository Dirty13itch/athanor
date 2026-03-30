import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("server-only", () => ({}));

describe("neo4j graph route", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalFixtureMode = env.DASHBOARD_FIXTURE_MODE;

  afterEach(() => {
    if (originalFixtureMode === undefined) {
      delete env.DASHBOARD_FIXTURE_MODE;
    } else {
      env.DASHBOARD_FIXTURE_MODE = originalFixtureMode;
    }
  });

  it("returns fixture graph data in fixture mode", async () => {
    env.DASHBOARD_FIXTURE_MODE = "1";
    const { GET } = await import("./route");

    const response = await GET(
      new NextRequest("http://localhost/api/neo4j/graph?limit=2&label=Service")
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      nodes: [
        { id: "service-agent-server", type: "Service" },
        { id: "service-dashboard", type: "Service" },
      ],
      links: [{ source: "service-dashboard", target: "service-agent-server", type: "PROXIES_TO" }],
      meta: { nodeCount: 2, linkCount: 1, limit: 2 },
    });
  });
});
