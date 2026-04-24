import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-summary", () => ({
  loadOperatorSummaryPayload: vi.fn(async () => ({
    steadyState: {
      currentObjective: "stable_operating_day",
    },
    projectFactory: {
      topPriorityProjectId: "eoq",
      topPriorityProjectLabel: "Empire of Broken Queens",
      pendingCandidateCount: 1,
    },
  })),
}));

import { GET } from "./route";
import { loadOperatorSummaryPayload } from "@/lib/operator-summary";

describe("operator summary api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns the canonical operator summary payload with project-factory state", async () => {
    const response = await GET();
    expect(response.status).toBe(200);
    expect(loadOperatorSummaryPayload).toHaveBeenCalledTimes(1);

    const payload = await response.json();
    expect(payload.steadyState.currentObjective).toBe("stable_operating_day");
    expect(payload.projectFactory.topPriorityProjectId).toBe("eoq");
    expect(payload.projectFactory.topPriorityProjectLabel).toBe("Empire of Broken Queens");
    expect(payload.projectFactory.pendingCandidateCount).toBe(1);
  });
});
