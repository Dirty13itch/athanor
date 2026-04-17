import { describe, expect, it, vi } from "vitest";

const { fetchJson } = vi.hoisted(() => ({
  fetchJson: vi.fn(async () => ({
    generatedAt: "2026-04-16T00:00:00.000Z",
    available: true,
    degraded: false,
    summary: {
      total: 0,
      formalEvalComplete: 0,
      formalEvalFailed: 0,
      manualReviewPending: 0,
      readyForFormalEval: 0,
      operatorSmokeOnly: 0,
      scaffoldOnly: 0,
      blocked: 0,
    },
    records: [],
  })),
}));

vi.mock("@/lib/http", () => ({
  fetchJson,
}));

import { capabilityPilotReadinessSnapshotSchema } from "@/lib/contracts";
import { getCapabilityPilotReadiness } from "./api";

describe("getCapabilityPilotReadiness", () => {
  it("fetches the operator pilot-readiness route with the typed snapshot schema", async () => {
    const result = await getCapabilityPilotReadiness();

    expect(result.available).toBe(true);
    expect(fetchJson).toHaveBeenCalledWith(
      "/api/operator/pilot-readiness",
      { cache: "no-store" },
      capabilityPilotReadinessSnapshotSchema,
    );
  });
});
