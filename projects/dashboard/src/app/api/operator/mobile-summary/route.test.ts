import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-mobile-summary", () => ({
  loadOperatorMobileSummary: vi.fn(async () => ({
    summary: {
      attentionLevel: "review_recommended",
      attentionLabel: "Review recommended",
      needsYou: true,
      currentObjective: "closure_debt",
      onlyTypedBrakesRemain: true,
      nextOperatorAction: "Review the runtime packet inbox and approve the next bounded mutation packet.",
      runtimePacketNext: {
        familyId: "runtime-packet-inbox",
        subtrancheId: "workshop-ulrich-energy-retirement-packet",
      },
      controller: {
        host: "dev",
        mode: "closure_debt",
        status: "running",
        activePassId: "continuity-pass-123",
        typedBrake: null,
      },
      proofGate: {
        open: false,
        blockingCheckIds: ["stable_operating_day", "result_backed_threshold"],
        thresholdProgress: 0,
        thresholdRequired: 5,
        coveredWindowHours: 0.0,
        requiredWindowHours: 24,
      },
      availableActions: ["observe", "approve", "deny", "pause", "resume", "inspect", "nudge"],
    },
    status: {
      available: true,
      degraded: false,
      detail: null,
      sourceKind: "workspace_report",
      sourcePath: "/mnt/c/Athanor/reports/truth-inventory/operator-mobile-summary.json",
    },
  })),
}));

import { GET } from "./route";
import { loadOperatorMobileSummary } from "@/lib/operator-mobile-summary";

describe("operator mobile-summary api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns the canonical phone-safe operator summary payload", async () => {
    const response = await GET();
    expect(response.status).toBe(200);
    expect(loadOperatorMobileSummary).toHaveBeenCalledTimes(1);

    const payload = await response.json();
    expect(payload.summary.attentionLevel).toBe("review_recommended");
    expect(payload.summary.onlyTypedBrakesRemain).toBe(true);
    expect(payload.summary.nextOperatorAction).toContain("runtime packet inbox");
    expect(payload.summary.runtimePacketNext.subtrancheId).toBe("workshop-ulrich-energy-retirement-packet");
    expect(payload.summary.controller.host).toBe("dev");
    expect(payload.status.sourcePath).toBe(
      "/mnt/c/Athanor/reports/truth-inventory/operator-mobile-summary.json",
    );
  });
});
