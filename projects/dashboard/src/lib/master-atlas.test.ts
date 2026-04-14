import { describe, expect, it } from "vitest";
import { pickMasterAtlasRelationshipMap } from "./master-atlas";

describe("pickMasterAtlasRelationshipMap", () => {
  it("preserves governed-dispatch restart resilience fields on the top-level execution summary", () => {
    const map = pickMasterAtlasRelationshipMap({
      generated_at: "2026-04-14T01:49:49.635616+00:00",
      governed_dispatch_execution: {
        status: "dispatched",
        dispatch_outcome: "success",
        task_id: "05a179ae09c3",
        task_status: "pending",
        task_source: "auto-retry",
        retry_of_task_id: "b84da0c191a6",
        retry_count: 1,
        retry_lineage_depth: 1,
        recovery_event: "stale_lease_recovered",
        recovery_reason: "server_restart",
        resilience_state: "restart_interfering",
        advisory_blockers: ["agent_runtime_restart_interfering"],
      },
      lane_recommendations: [],
    });

    expect(map?.governed_dispatch_execution).toMatchObject({
      task_source: "auto-retry",
      retry_of_task_id: "b84da0c191a6",
      retry_count: 1,
      retry_lineage_depth: 1,
      recovery_event: "stale_lease_recovered",
      recovery_reason: "server_restart",
      resilience_state: "restart_interfering",
      advisory_blockers: ["agent_runtime_restart_interfering"],
    });
  });

  it("reads Goose adoption truth from capability registry capabilities and preserves summary fields", () => {
    const map = pickMasterAtlasRelationshipMap({
      generated_at: "2026-04-14T16:40:00.000000+00:00",
      dashboard_summary: {
        generated_at: "2026-04-14T16:40:00.000000+00:00",
        capability_count: 1,
        adopted_count: 1,
        packet_ready_count: 0,
        proving_count: 0,
        blocked_capability_count: 0,
        blocked_packet_count: 0,
        governance_posture: "healthy",
        governance_blocker_count: 0,
        governance_blockers: [],
        turnover_status: "ready",
        turnover_ready_now: true,
        turnover_current_mode: "shadow",
        turnover_target_mode: "low_touch",
        turnover_blocker_count: 0,
        goose_stage: "adopted",
        goose_readiness: "formal_eval_complete",
        goose_next_gate: "Maintain the adopted bounded shell path; future shell-path changes stay packet-backed.",
        goose_next_action: "Keep Goose as the adopted bounded shell path and packet any future shell-boundary changes.",
        recommendation_summaries: [],
      },
      capability_pilot_readiness: {
        records: [
          {
            capability_id: "goose-operator-shell",
            label: "Goose Operator Shell",
            readiness_state: "formal_eval_complete",
            formal_eval_status: "passed",
            formal_eval_at: "2026-04-14T16:01:37.578068+00:00",
            formal_eval_promptfoo_summary: {
              successes: 8,
              failures: 0,
              errors: 0,
              duration_ms: 137317,
            },
            request_surface_hint: "dashboard-routed bounded shell task",
            next_action: "Advance this lane into packet review, promotion, or explicit bounded retention.",
            next_formal_gate: "Formal eval is complete; move this lane to promotion or bounded retention decision.",
            packet_path: "C:/athanor-devstack/docs/promotion-packets/goose-operator-shell.md",
            command_checks: [
              {
                command: "goose",
                available_locally: true,
                inventory_status: "installed",
                inventory_version: "1.30.0",
                local_path: "C:/Users/Shaun/.local/bin/goose.EXE",
              },
            ],
          },
        ],
      },
      capability_adoption_registry: {
        capabilities: [
          {
            id: "goose-operator-shell",
            stage: "adopted",
            authority_class: "adopted_system",
            source_safe_remaining: [],
            approval_gated_remaining: [],
          },
        ],
      },
      capability_pilot_evals: {
        records: [
          {
            capability_id: "goose-operator-shell",
            operator_test_status: "passed",
          },
        ],
      },
      lane_recommendations: [],
    });

    expect(map?.summary).toMatchObject({
      goose_stage: "adopted",
      goose_readiness: "formal_eval_complete",
    });
    expect(map?.goose_evidence_summary).toMatchObject({
      packet_status: "adopted",
      source_safe_remaining: [],
      approval_gated_remaining: [],
      command_inventory_status: "installed",
    });
  });
});
