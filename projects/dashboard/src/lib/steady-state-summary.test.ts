import { describe, expect, it } from "vitest";
import { buildSteadyStateDecisionSummary, getSteadyStateAttentionTone } from "./steady-state-summary";

describe("steady-state summary", () => {
  it("derives healthy attention and provenance from a steady-state snapshot", () => {
    const summary = buildSteadyStateDecisionSummary({
      generatedAt: "2026-04-16T00:00:00.000Z",
      closureState: "repo_safe_complete",
      operatorMode: "steady_state_monitoring",
      interventionLabel: "No action needed",
      interventionLevel: "no_action_needed",
      interventionSummary: "Queue is moving without operator intervention.",
      needsYou: false,
      nextOperatorAction: "Keep monitoring.",
      queueDispatchable: 2,
      queueTotal: 5,
      suppressedTaskCount: 3,
      runtimePacketCount: 0,
      currentWork: {
        taskTitle: "Cheap Bulk Cloud",
        providerLabel: "deepseek_api",
        laneFamily: "capacity_truth_repair",
      },
      nextUp: {
        taskTitle: "Letta Memory Plane",
        providerLabel: "Athanor Local",
        laneFamily: "memory_plane",
      },
      sourceKind: "workspace_report",
      sourcePath: "/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json",
    });

    expect(summary.attentionTone).toBe("warning");
    expect(summary.currentWorkDetail).toContain("deepseek_api");
    expect(summary.nextUpTitle).toBe("Letta Memory Plane");
    expect(summary.sourceLabel).toBe("workspace report");
  });

  it("falls back cleanly when steady-state is unavailable", () => {
    const summary = buildSteadyStateDecisionSummary(null, {
      attentionLabel: "feed offline",
      attentionSummary: "Operator feed is temporarily unavailable.",
      currentWorkTitle: "No governed work published.",
      currentWorkDetail: "Fallback lane detail.",
      nextUpTitle: "No follow-on handoff published.",
      nextUpDetail: "No next operator action published.",
      queuePosture: "4 queued / 1 approval",
      needsYou: true,
    });

    expect(summary.attentionTone).toBe("danger");
    expect(summary.attentionLabel).toBe("feed offline");
    expect(summary.sourceLabel).toBe("steady-state feed unavailable");
    expect(summary.queuePosture).toBe("4 queued / 1 approval");
  });

  it("treats runtime packets as danger even without explicit needs-you", () => {
    expect(
      getSteadyStateAttentionTone({
        generatedAt: "2026-04-16T00:00:00.000Z",
        closureState: "closure_in_progress",
        operatorMode: "active_closure",
        interventionLabel: "Approval required",
        interventionLevel: "approval_required",
        interventionSummary: "Runtime packets are waiting.",
        needsYou: false,
        nextOperatorAction: "Approve runtime packets.",
        queueDispatchable: 0,
        queueTotal: 0,
        suppressedTaskCount: 0,
        runtimePacketCount: 2,
        currentWork: null,
        nextUp: null,
      }),
    ).toBe("danger");
  });
});
