import { describe, expect, it } from "vitest";
import {
  normalizePipelineOutcomes,
  normalizePipelinePlans,
  normalizePipelineProposals,
  normalizePipelineStatus,
} from "./pipeline-normalization";

describe("pipeline normalization", () => {
  it("normalizes compatibility pipeline payloads", () => {
    const status = normalizePipelineStatus({
      recent_cycles: [
        {
          id: "cycle-1",
          completed_at: "2026-03-30T09:00:00.000Z",
        },
      ],
      pending_plans: 2,
      recent_outcomes_count: 5,
      avg_quality: 0.92,
      last_cycle: {
        completed_at: "2026-03-30T09:00:00.000Z",
      },
    });
    const plans = normalizePipelinePlans({
      plans: [
        {
          id: "plan-1",
          title: "Promote command-center IA slice to trunk",
          status: "pending",
        },
      ],
    });
    const outcomes = normalizePipelineOutcomes({
      outcomes: [
        {
          id: "outcome-1",
          plan_id: "plan-1",
          status: "accepted",
          quality: 0.94,
          recorded_at: "2026-03-30T09:05:00.000Z",
        },
      ],
    });
    const proposals = normalizePipelineProposals({
      proposals: [
        {
          title: "Commit command-center IA lane",
          confidence: 0.88,
          requires_approval: true,
        },
      ],
    });

    expect(status).toEqual({
      recent_cycles: 1,
      pending_plans: 2,
      recent_outcomes_count: 5,
      avg_quality: 0.92,
      last_cycle: "2026-03-30T09:00:00.000Z",
    });
    expect(plans[0]).toMatchObject({
      id: "plan-1",
      intent_source: "pending",
      approach: "Promote command-center IA slice to trunk",
      risk_level: "medium",
      status: "pending",
    });
    expect(outcomes[0]).toMatchObject({
      task_id: "outcome-1",
      prompt: "plan-1",
      quality_score: 0.94,
      success: true,
      ts: "2026-03-30T09:05:00.000Z",
    });
    expect(proposals[0]).toMatchObject({
      text: "Commit command-center IA lane",
      priority: 0.88,
      project: "general",
      agent: "pipeline",
      explore: false,
    });
  });

  it("preserves canonical pipeline payloads", () => {
    const status = normalizePipelineStatus({
      recent_cycles: 3,
      pending_plans: 1,
      recent_outcomes_count: 4,
      avg_quality: 0.75,
      last_cycle: "2026-03-30T10:00:00.000Z",
    });
    const plans = normalizePipelinePlans([
      {
        id: "plan-2",
        title: "Queue runtime-deploy ansible slice",
        intent_source: "athanor",
        approach: "Prepare the repo-safe deploy tranche.",
        risk_level: "high",
        status: "pending",
      },
    ]);

    expect(status).toEqual({
      recent_cycles: 3,
      pending_plans: 1,
      recent_outcomes_count: 4,
      avg_quality: 0.75,
      last_cycle: "2026-03-30T10:00:00.000Z",
    });
    expect(plans[0]).toMatchObject({
      intent_source: "athanor",
      approach: "Prepare the repo-safe deploy tranche.",
      risk_level: "high",
    });
  });
});
