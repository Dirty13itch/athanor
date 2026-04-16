import { describe, expect, it, vi } from "vitest";

const { proxyAgentJson } = vi.hoisted(() => ({
  proxyAgentJson: vi.fn(),
}));

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson,
}));

import { GET } from "./route";

describe("GET /api/pipeline/status", () => {
  it("returns the compatibility payload when the upstream status surface is unavailable", async () => {
    proxyAgentJson.mockResolvedValueOnce(new Response(null, { status: 502 }));

    const response = await GET();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      recent_cycles: [],
      pending_plans: [],
      recent_outcomes_count: 0,
      avg_quality: null,
      last_cycle: null,
      status: "unavailable",
      message: "Pipeline status not yet implemented in Agent Server",
    });
  });
});
