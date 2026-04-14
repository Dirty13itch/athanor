import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MasterAtlasRelationshipPanel } from "./master-atlas-relationship-panel";

describe("MasterAtlasRelationshipPanel", () => {
  it("renders the federated authority surfaces and promotion flow", () => {
    render(
      <MasterAtlasRelationshipPanel
        map={{
          generated_at: "2026-04-10T00:00:00Z",
          summary: {
            capability_count: 6,
            adopted_count: 1,
            packet_ready_count: 2,
            proving_count: 3,
            blocked_packet_count: 5,
            governance_posture: "blocked",
            governance_blockers: ["constrained-mode"],
            best_next_implementation_wave: "graphrag-hybrid-retrieval",
            best_next_promotion_candidate: "graphrag-hybrid-retrieval",
            turnover_status: "devstack_primary_build_only",
            turnover_ready_now: false,
            turnover_next_gate: "governance:constrained-mode",
            turnover_current_mode: "devstack_primary_for_build_and_proving",
            turnover_target_mode: "local_devstack_primary_for_low_touch_execution",
            turnover_blocker_count: 3,
            checkpoint_slice_count: 6,
            checkpoint_slice_ready_for_checkpoint_count: 4,
            next_checkpoint_slice: {
              id: "backbone-contracts-and-truth-writers",
              title: "Backbone Contracts and Truth Writers",
              order: 1,
              status: "ready_for_checkpoint",
              blocking_gate: "none",
              owner_workstreams: ["authority-and-mainline", "validation-and-publication"],
            },
          },
          turnover_readiness: {
            current_mode: "devstack_primary_for_build_and_proving",
            target_mode: "local_devstack_primary_for_low_touch_execution",
            autonomous_turnover_status: "devstack_primary_build_only",
            autonomous_turnover_ready_now: false,
            next_gate: "governance:constrained-mode",
            blocker_count: 3,
            blockers: ["governance:constrained-mode", "formal_eval_runs_missing"],
            autonomous_queue_count: 5,
            dispatchable_autonomous_queue_count: 2,
            dispatchable_safe_surface_queue_count: 1,
            top_dispatchable_autonomous_task_id: "workstream:provider-and-secret-remediation",
            top_dispatchable_autonomous_task_title: "Repair blocked provider and secret lanes",
            work_economy_status: "degraded",
            work_economy_ready_now: false,
            work_economy_blocked_burn_class_ids: [],
            work_economy_degraded_burn_class_ids: ["cheap_bulk_cloud"],
            burn_dispatch_phase: 1,
            burn_dispatch_phase_label: "governed_dispatch_shadow",
            required_before_turnover: [
              "Pass and refresh the constrained-mode, degraded-mode, and recovery-only governance drills.",
              "Record at least one formal promotion-valid eval run for the selected implementation wave.",
            ],
            operator_answer:
              "Devstack already owns build and proving work. Turn over unattended local implementation only after governance drills are healthy, evals are promotion-valid, and runtime packet linkage is complete.",
            checkpoint_slice_summary: {
              sequence_id: "2026-04-12-bounded-checkpoint-publication",
              total: 6,
              ready_for_checkpoint: 4,
              active: 1,
              approval_gated: 1,
              published: 0,
            },
            next_checkpoint_slice: {
              id: "backbone-contracts-and-truth-writers",
              title: "Backbone Contracts and Truth Writers",
              order: 1,
              status: "ready_for_checkpoint",
              blocking_gate: "none",
              owner_workstreams: ["authority-and-mainline", "validation-and-publication"],
            },
          },
          authority_surfaces: [
            {
              id: "athanor",
              label: "Athanor",
              authority_class: "adopted_system",
              root: "C:/Athanor",
              role: "Canonical adopted-system and runtime-governance truth.",
              front_door: "/operator",
            },
            {
              id: "devstack",
              label: "Devstack",
              authority_class: "build_system",
              root: "C:/athanor-devstack",
              role: "Capability forge, proof system, and packet-drafting lane.",
              front_door: "/topology",
            },
          ],
          promotion_flow: {
            source_label: "Devstack proof lanes",
            packet_ready_count: 2,
            next_promotion_candidate: "graphrag-hybrid-retrieval",
            target_label: "Athanor adopted truth",
            governance_posture: "blocked",
          },
          blocked_packets: [
            {
              packet_id: "pending-graphrag-hybrid-retrieval",
              capability_id: "graphrag-hybrid-retrieval",
              blocked_by: ["release_tier_not_advanced"],
              runtime_target: "Athanor agents knowledge and retrieval surfaces",
            },
          ],
          node_capacity: [
            {
              node_id: "foundry",
              node_role: "heavy_compute",
              gpu_count: 5,
              interactive_reserve_gpu_slots: 1,
              background_fill_gpu_slots: 4,
              utilization_targets: {
                interactive_reserve_floor_gpu_slots: 1,
                background_harvest_target_gpu_slots: 3,
                max_noncritical_preemptible_gpu_slots: 4,
              },
            },
          ],
          dispatch_lanes: [
            {
              lane_id: "sovereign_coder",
              provider_id: "athanor_local",
              reserve_class: "interactive_local",
              max_parallel_slots: 4,
              reserved_parallel_slots: 2,
              harvestable_parallel_slots: 2,
              selection_reason: "Best sunk-cost lane for private implementation and domain automation.",
            },
          ],
          quota_posture: {
            quota_posture: "max_burn_with_thin_reserve",
            respect_vendor_policy_before_harvest: true,
            other_metered_disabled_for_auto_harvest_by_default: true,
            record_count: 6,
            degraded_record_count: 1,
            low_confidence_record_count: 0,
            degraded_records: [
              {
                family_id: "glm_coding_plan",
                degraded_reason: "supported_tool_usage_observed",
              },
            ],
            local_compute_capacity: {
              remaining_units: 5,
              sample_posture: "scheduler_projection_backed",
              scheduler_queue_depth: 0,
              scheduler_slot_count: 5,
              harvestable_scheduler_slot_count: 2,
              harvestable_by_zone: {
                F: 4,
                W: 1,
              },
              harvestable_by_slot: {
                "F:TP4": 4,
                "W:1": 1,
              },
              provisional_harvest_candidate_count: 1,
              provisional_harvestable_by_node: {
                vault: 1,
              },
              open_harvest_slot_ids: ["F:TP4", "W:1"],
              open_harvest_slot_target_ids: ["foundry-bulk-pool", "workshop-batch-support"],
              scheduler_conflict_gpu_count: 0,
            },
          },
          router_shadow_summary: {
            phase: 0,
            phase_label: "build_ledgers_and_emit_recommendations_only",
            shadow_disagreement_rate: 0,
            routing_proof_total: 16,
            routing_proof_failed: 0,
            ready_for_phase_1: true,
            ready_for_phase_2: true,
          },
          next_required_approval: {
            approval_class: "review_required",
            label: "Review recommend-only outputs before shadow rollout",
            reason: "Router remains in phase 0 recommend-only mode.",
            allowed_actions: ["promotion_packet_update", "lane_eval_update"],
          },
          safe_surface_summary: {
            last_outcome: "healthy",
            last_success_at: "2026-04-10T00:00:00Z",
            current_task_id: null,
            on_deck_task_id: "safe-123",
            queue_count: 2,
            current_task_threads: 1,
          },
          autonomous_queue_summary: {
            queue_count: 5,
            dispatchable_queue_count: 2,
            blocked_queue_count: 3,
            top_dispatchable_task_id: "workstream:provider-and-secret-remediation",
            top_dispatchable_title: "Repair blocked provider and secret lanes",
            top_dispatchable_value_class: "provider_auth_drift",
            top_dispatchable_lane_family: "operator_approval_required",
          },
          governed_dispatch_execution: {
            status: "already_dispatched",
            dispatch_outcome: "claimed",
            backlog_id: "backlog-d13e5ae5",
            backlog_status: "waiting_approval",
            task_id: "task-82b58ccd1fa5",
            task_status: "pending_approval",
            governor_level: "C",
            governor_reason: "Level C (score=0.48), owner away - deferred",
            repaired_stale_task_id: "task-old",
            report_path: "reports/truth-inventory/governed-dispatch-execution.json",
          },
          lane_recommendations: [
            {
              task_class: "multi_file_implementation",
              sensitivity_class: "private_but_cloud_allowed",
              preferred_lane: "codex_cloudsafe",
              secondary_lane: "sovereign_coder",
              overflow_lane: "glm_cloudsafe_bulk",
              default_execution_mode: "direct_cli",
              provider: "openai_responses",
              runtime: "remote",
              privacy: "cloud_safe_only",
              degraded: false,
              degraded_failure_class: null,
              selection_reason: "Prefer premium implementation quality first.",
              quota_signal: {
                provider_or_family: "openai_codex",
                confidence: "high",
                remaining_units: 42,
                budget_remaining_usd: null,
                degraded_reason: null,
              },
            },
          ],
        }}
      />
    );

    expect(screen.getByText("Master Atlas Relationship Map")).toBeInTheDocument();
    expect(screen.getByText("Athanor")).toBeInTheDocument();
    expect(screen.getByText("Devstack")).toBeInTheDocument();
    expect(screen.getByText("Devstack proof lanes")).toBeInTheDocument();
    expect(screen.getByText("Athanor adopted truth")).toBeInTheDocument();
    expect(screen.getByText("sovereign coder")).toBeInTheDocument();
    expect(screen.getAllByText("graphrag hybrid retrieval").length).toBeGreaterThan(0);
    expect(screen.getByText("Turnover Readiness")).toBeInTheDocument();
    expect(screen.getByText("Checkpoint publication")).toBeInTheDocument();
    expect(screen.getByText("Backbone Contracts and Truth Writers")).toBeInTheDocument();
    expect(screen.getByText("Routing and Quota Posture")).toBeInTheDocument();
    expect(screen.getByText("Autonomous queue")).toBeInTheDocument();
    expect(screen.getByText(/Repair blocked provider and secret lanes/)).toBeInTheDocument();
    expect(screen.getByText("Governed dispatch handoff")).toBeInTheDocument();
    expect(screen.getByText(/governor c/i)).toBeInTheDocument();
    expect(screen.getByText("repaired task-old")).toBeInTheDocument();
    expect(screen.getByText("Work economy")).toBeInTheDocument();
    expect(screen.getByText("Local harvest window")).toBeInTheDocument();
    expect(screen.getByText("degraded cheap bulk cloud")).toBeInTheDocument();
    expect(screen.getByText("glm coding plan | supported tool usage observed")).toBeInTheDocument();
    expect(screen.getByText("5 local units available")).toBeInTheDocument();
    expect(screen.getByText("provisional outside scheduler 1")).toBeInTheDocument();
    expect(screen.getByText("provisional vault:1")).toBeInTheDocument();
    expect(screen.getByText("zone F:4")).toBeInTheDocument();
    expect(screen.getByText("target foundry bulk pool")).toBeInTheDocument();
    expect(screen.getByText("Lane Recommendations")).toBeInTheDocument();
  });
});
