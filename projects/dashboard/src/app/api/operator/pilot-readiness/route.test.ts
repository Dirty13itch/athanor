import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/capability-pilot-readiness", () => ({
  loadCapabilityPilotReadiness: vi.fn(async () => ({
    generatedAt: "2026-04-16T00:00:00.000Z",
    available: true,
    degraded: false,
    detail: null,
    sourceKind: "workspace_generated_atlas",
    sourcePath: "/mnt/c/Athanor/projects/dashboard/src/generated/master-atlas.json",
    summary: {
      total: 3,
      formalEvalComplete: 0,
      formalEvalFailed: 1,
      manualReviewPending: 0,
      readyForFormalEval: 0,
      operatorSmokeOnly: 0,
      scaffoldOnly: 0,
      blocked: 2,
    },
    records: [],
  })),
}));

import { GET } from "./route";
import { loadCapabilityPilotReadiness } from "@/lib/capability-pilot-readiness";

describe("operator pilot-readiness api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns the pilot-readiness snapshot from the dashboard data layer", async () => {
    const response = await GET();

    expect(response.status).toBe(200);
    expect(loadCapabilityPilotReadiness).toHaveBeenCalledTimes(1);
    await expect(response.json()).resolves.toMatchObject({
      available: true,
      degraded: false,
      sourceKind: "workspace_generated_atlas",
      summary: {
        total: 3,
        blocked: 2,
        formalEvalFailed: 1,
      },
    });
  });

  it("falls back to a degraded response if the data layer throws", async () => {
    vi.mocked(loadCapabilityPilotReadiness).mockRejectedValueOnce(new Error("boom"));

    const response = await GET();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      available: false,
      degraded: true,
      detail: expect.stringMatching(/Failed to load capability pilot readiness/i),
      summary: {
        total: 0,
        blocked: 0,
      },
      records: [],
    });
  });
});
