import { describe, expect, it } from "vitest";
import {
  classifyScheduledJobAdmission,
  classifyScheduledJobExecutionPlane,
  classifyScheduledJobExecutionMode,
  isScheduledJobBlocked,
  isScheduledJobProposalOnly,
  isScheduledJobQueueBacked,
  scheduledJobNeedsSync,
} from "./scheduled-job-posture";

describe("scheduled-job-posture", () => {
  it("keeps coding-agent and research schedules in the queue-backed lane", () => {
    expect(
      classifyScheduledJobExecutionMode({
        id: "agent-schedule:coding-agent",
        last_execution_mode: null,
      }),
    ).toBe("materialized_to_backlog");

    expect(
      classifyScheduledJobExecutionMode({
        id: "research:provider-drift",
        last_execution_mode: null,
      }),
    ).toBe("materialized_to_backlog");

    expect(
      classifyScheduledJobExecutionMode({
        id: "daily-digest",
        last_execution_mode: null,
      }),
    ).toBe("executed_directly");

    expect(
      classifyScheduledJobExecutionPlane({
        id: "improvement-cycle",
        last_execution_mode: "executed_directly",
        last_execution_plane: null,
      }),
    ).toBe("proposal_only");
  });

  it("flags only stale backlog-backed jobs as needs sync", () => {
    expect(
      scheduledJobNeedsSync({
        id: "research:provider-drift",
        last_execution_mode: "materialized_to_backlog",
        last_backlog_id: null,
      }),
    ).toBe(true);

    expect(
      scheduledJobNeedsSync({
        id: "research:provider-drift",
        last_execution_mode: null,
        last_backlog_id: null,
      }),
    ).toBe(false);

    expect(
      isScheduledJobQueueBacked({
        id: "daily-digest",
        last_execution_mode: "executed_directly",
        last_execution_plane: "direct_control",
      }),
    ).toBe(false);
  });

  it("classifies proposal-only and blocked admissions distinctly", () => {
    expect(
      isScheduledJobProposalOnly({
        id: "nightly-optimization",
        last_execution_mode: "executed_directly",
        last_execution_plane: null,
      }),
    ).toBe(true);

    expect(
      classifyScheduledJobAdmission({
        id: "improvement-cycle",
        last_execution_mode: "executed_directly",
        last_execution_plane: "proposal_only",
        last_admission_classification: "blocked_by_review_debt",
      }),
    ).toBe("blocked_by_review_debt");

    expect(
      isScheduledJobBlocked({
        id: "improvement-cycle",
        last_execution_mode: "executed_directly",
        last_execution_plane: "proposal_only",
        last_admission_classification: "blocked_by_review_debt",
      }),
    ).toBe(true);
  });
});
