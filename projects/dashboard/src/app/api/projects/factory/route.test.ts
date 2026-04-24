import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/project-factory", () => ({
  loadProjectFactorySnapshot: vi.fn(async () => ({
    generatedAt: "2026-04-20T22:00:00+00:00",
    available: true,
    degraded: false,
    detail: null,
    summary: {
      topPriorityProjectId: "eoq",
      topPriorityProjectLabel: "Empire of Broken Queens",
      acceptedProjectOutputCount: 0,
      pendingCandidateCount: 1,
      pendingHybridAcceptanceCount: 1,
    },
  })),
}));

import { GET } from "./route";
import { loadProjectFactorySnapshot } from "@/lib/project-factory";

describe("project factory api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns the governed project-factory snapshot as JSON", async () => {
    const response = await GET();
    expect(response.status).toBe(200);
    expect(loadProjectFactorySnapshot).toHaveBeenCalledTimes(1);

    const payload = await response.json();
    expect(payload.summary.topPriorityProjectId).toBe("eoq");
    expect(payload.summary.topPriorityProjectLabel).toBe("Empire of Broken Queens");
    expect(payload.summary.pendingCandidateCount).toBe(1);
  });
});
