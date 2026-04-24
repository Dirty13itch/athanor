import { describe, expect, it } from "vitest";
import {
  getBuilderKernelPressureLabel,
  getBuilderKernelPressureTone,
  summarizeBuilderKernelPressure,
} from "./builder-kernel-pressure";

const baseBuilderFrontDoor = {
  available: true,
  degraded: false,
  detail: null,
  updated_at: "2026-04-18T00:00:00.000Z",
  session_count: 1,
  active_count: 1,
  pending_approval_count: 1,
  recent_artifact_count: 0,
  shared_pressure: {
    pending_review_count: 0,
    actionable_result_count: 0,
    current_session_pending_review_count: 0,
    current_session_actionable_result_count: 0,
    current_session_status: "ready" as const,
    current_session_needs_sync: false,
  },
  current_session: {
    id: "builder-1",
    title: "Implement the first builder route",
    status: "waiting_approval" as const,
    primary_adapter: "codex",
    current_route: "Codex direct implementation",
    verification_status: "planned" as const,
    pending_approval_count: 1,
    artifact_count: 0,
    resumable_handle: null,
    shadow_mode: false,
    fallback_state: "approval_pending",
    updated_at: "2026-04-18T00:00:00.000Z",
  },
  sessions: [],
};

describe("builder kernel pressure", () => {
  it("marks stale approval-only builder state as needs sync without shared review evidence", () => {
    const sharedPressure = summarizeBuilderKernelPressure(baseBuilderFrontDoor, [], []);
    const enriched = { ...baseBuilderFrontDoor, shared_pressure: sharedPressure };

    expect(sharedPressure.current_session_needs_sync).toBe(true);
    expect(sharedPressure.current_session_status).toBe("needs_sync");
    expect(getBuilderKernelPressureTone(enriched)).toBe("warning");
    expect(getBuilderKernelPressureLabel(enriched)).toBe("needs sync");
  });

  it("treats pending builder reviews as the authoritative approval pressure", () => {
    const sharedPressure = summarizeBuilderKernelPressure(
      baseBuilderFrontDoor,
      [
        {
          id: "builder-review-1",
          family: "builder",
          source: "builder_front_door",
          owner_kind: "session",
          owner_id: "builder-1",
          related_run_id: "builder-run-1",
          related_task_id: "builder-1",
          requested_action: "approve",
          privilege_class: "admin",
          reason: "Approve the builder packet.",
          status: "pending",
          requested_at: 100,
          task_prompt: "Implement the first builder route",
          task_agent_id: "codex",
          task_priority: "high",
          task_status: "pending_approval",
          deep_link: "/review?selection=builder-review-1",
          metadata: {},
        },
      ],
      [],
    );
    const enriched = { ...baseBuilderFrontDoor, shared_pressure: sharedPressure };

    expect(sharedPressure.pending_review_count).toBe(1);
    expect(sharedPressure.current_session_pending_review_count).toBe(1);
    expect(sharedPressure.current_session_needs_sync).toBe(false);
    expect(sharedPressure.current_session_status).toBe("review_required");
    expect(getBuilderKernelPressureTone(enriched)).toBe("warning");
    expect(getBuilderKernelPressureLabel(enriched)).toBe("review pending");
  });

  it("treats shared actionable builder results as failure pressure", () => {
    const sharedPressure = summarizeBuilderKernelPressure(
      {
        ...baseBuilderFrontDoor,
        pending_approval_count: 0,
        current_session: {
          ...baseBuilderFrontDoor.current_session,
          status: "failed",
          pending_approval_count: 0,
          verification_status: "failed",
          fallback_state: null,
        },
      },
      [],
      [
        {
          id: "builder-result-1",
          family: "builder",
          source: "builder_front_door",
          owner_kind: "session",
          owner_id: "builder-1",
          related_run_id: "builder-run-1",
          status: "failed",
          outcome: "failed",
          summary: "Verification failed.",
          artifact_count: 0,
          artifacts: [],
          files_changed: [],
          validation: [],
          remaining_risks: ["verification failed"],
          resumable_handle: null,
          recovery_gate: null,
          verification_status: "failed",
          updated_at: "2026-04-18T00:00:00.000Z",
          deep_link: "/review?selection=builder-result-1",
          metadata: {},
        },
      ],
    );
    const enriched = { ...baseBuilderFrontDoor, shared_pressure: sharedPressure };

    expect(sharedPressure.actionable_result_count).toBe(1);
    expect(sharedPressure.current_session_actionable_result_count).toBe(1);
    expect(sharedPressure.current_session_status).toBe("result_attention");
    expect(getBuilderKernelPressureTone(enriched)).toBe("danger");
    expect(getBuilderKernelPressureLabel(enriched)).toBe("result attention");
  });
});
