import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ModelGovernanceCard } from "./model-governance-card";

const { getModelGovernance, requestJson, useOperatorSessionStatus, isOperatorSessionLocked } = vi.hoisted(() => ({
  getModelGovernance: vi.fn(),
  requestJson: vi.fn(),
  useOperatorSessionStatus: vi.fn(),
  isOperatorSessionLocked: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  getModelGovernance,
}));

vi.mock("@/features/workforce/helpers", () => ({
  requestJson,
}));

vi.mock("@/lib/operator-session", () => ({
  useOperatorSessionStatus,
  isOperatorSessionLocked,
}));

function buildWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe("ModelGovernanceCard", () => {
  it("surfaces shared capability posture alongside the existing governance ladders", async () => {
    useOperatorSessionStatus.mockReturnValue({ isPending: false });
    isOperatorSessionLocked.mockReturnValue(false);
    getModelGovernance.mockResolvedValue({
      generated_at: "2026-04-17T03:00:00.000Z",
      role_registry_version: "2026-04-17.1",
      workload_registry_version: "2026-04-17.1",
      rights_registry_version: "2026-04-17.1",
      policy_registry_version: "2026-04-17.1",
      role_count: 1,
      workload_count: 1,
      champion_summary: [
        {
          role_id: "builder",
          label: "Builder",
          plane: "execution",
          status: "live",
          champion: "openai_codex",
          challenger_count: 1,
          workload_count: 2,
        },
      ],
      role_registry: [
        {
          id: "builder",
          label: "Builder",
          plane: "execution",
          status: "live",
          champion: "openai_codex",
          challengers: ["anthropic_claude_code"],
          workload_classes: ["multi_file_implementation", "repo_wide_audit"],
        },
      ],
      workload_registry: [
        {
          id: "multi_file_implementation",
          label: "Multi-file implementation",
          policy_default: "private_but_cloud_allowed",
          frontier_supervisor: "frontier_supervisor",
          sovereign_supervisor: "sovereign_supervisor",
          primary_worker_lane: "coding_worker",
          fallback_worker_lanes: ["bulk_worker"],
          judge_lane: "judge_verifier",
          default_autonomy: "C",
          parallelism: "manager_first",
        },
      ],
      proving_ground: {
        version: "2026-04-17.1",
        status: "live",
        purpose: "Evaluate and promote model lanes.",
        evaluation_dimensions: ["quality", "latency"],
        corpora: [{ id: "golden_tasks", sensitivity: "mixed", allowed_lanes: ["frontier_cloud"], purpose: "proof" }],
        pipeline_phases: ["benchmark", "promote"],
        promotion_path: ["candidate", "shadow", "promote"],
        rollback_rule: "rollback on regression",
        recent_results: [],
        promotion_controls: {
          generated_at: "2026-04-17T03:00:00.000Z",
          status: "live_partial",
          tiers: ["canary"],
          ritual: ["prove", "promote"],
          counts: {},
          active_promotions: [],
          recent_promotions: [],
          recent_events: [],
          candidate_queue: [],
          next_actions: ["Stage the next challenger."],
        },
      },
      promotion_controls: {
        generated_at: "2026-04-17T03:00:00.000Z",
        status: "live_partial",
        tiers: ["canary"],
        ritual: ["prove", "promote"],
        counts: {},
        active_promotions: [],
        recent_promotions: [],
        recent_events: [],
        candidate_queue: [],
        next_actions: ["Stage the next challenger."],
      },
      retirement_controls: {
        generated_at: "2026-04-17T03:00:00.000Z",
        status: "live_partial",
        asset_classes: ["models"],
        stages: ["active", "retiring"],
        rule: "Retire only after rollback proof.",
        counts: {},
        active_retirements: [],
        recent_retirements: [],
        recent_events: [],
        candidate_queue: [],
        next_actions: ["Exercise a retirement rehearsal."],
      },
      model_intelligence: {
        version: "2026-04-17.1",
        updated_at: "2026-04-17T03:00:00.000Z",
        status: "live",
        generated_at: "2026-04-17T03:00:00.000Z",
        operational_state: "active",
        cadence: {
          weekly_horizon_scan: "every Monday",
          weekly_candidate_triage: "every Tuesday",
          monthly_rebaseline: "first Saturday",
          urgent_scan: "major release",
        },
        sources: ["release notes"],
        outputs: ["candidate queue"],
        guardrails: ["no promotion without proof"],
        benchmark_results: 4,
        pending_proposals: 1,
        validated_proposals: 1,
        deployed_proposals: 0,
        candidate_queue: [
          {
            role_id: "builder",
            label: "Builder",
            plane: "execution",
            champion: "openai_codex",
            challengers: ["anthropic_claude_code"],
          },
        ],
        last_cycle: {
          timestamp: "2026-04-17T02:00:00.000Z",
          patterns_consumed: 2,
          proposals_generated: 1,
          benchmarks: {
            passed: 3,
            total: 4,
            pass_rate: 0.75,
          },
        },
        cadence_jobs: [
          {
            id: "weekly-scan",
            title: "Weekly horizon scan",
            cadence: "weekly",
            current_state: "scheduled",
            last_run: "2026-04-16T03:00:00.000Z",
            next_run: "2026-04-23T03:00:00.000Z",
            last_outcome: "completed",
            paused: false,
            governor_reason: null,
          },
        ],
        next_actions: ["Review degraded capability subjects before widening lanes."],
      },
      capability_intelligence: {
        generated_at: "2026-04-17T03:00:00.000Z",
        version: "2026-04-17.1",
        status: "live",
        source_of_truth: "reports/truth-inventory/capability-intelligence.json",
        provider_count: 48,
        local_endpoint_count: 19,
        degraded_subject_count: 1,
        implementation: {
          subject_id: "openai_codex",
          task_class: "multi_file_implementation",
          capability_score: 91,
          demotion_state: "healthy",
          reserve_class: "premium_async",
        },
        audit: {
          subject_id: "google_gemini",
          task_class: "repo_wide_audit",
          capability_score: 89,
          demotion_state: "healthy",
          reserve_class: "burn_early_audit",
        },
        local_endpoint: {
          subject_id: "foundry-coder-lane",
          task_class: "multi_file_implementation",
          capability_score: 95,
          demotion_state: "healthy",
          reserve_class: "interactive_local_reserve",
        },
        next_actions: ["Repair degraded or demoted capability subjects before widening auto-routing."],
      },
      governance_layers: {
        contract_registry: {
          version: "2026-04-17.1",
          status: "live",
          count: 1,
          contracts: [
            {
              id: "artifact-provenance",
              label: "Artifact Provenance",
              owner: "kernel",
              purpose: "Track outputs",
              status: "live",
            },
          ],
          status_counts: { live: 1 },
          provenance_contract: {
            id: "artifact-provenance",
            label: "Artifact Provenance",
            owner: "kernel",
            purpose: "Track outputs",
            status: "live",
          },
        },
        eval_corpora: {
          version: "2026-04-17.1",
          status: "live",
          count: 1,
          corpora: [
            {
              id: "golden_tasks",
              label: "Golden Tasks",
              workload_classes: ["multi_file_implementation"],
              sensitivity: "mixed",
              allowed_lanes: ["frontier_cloud"],
              refresh_cadence: "weekly",
              baseline_version: "2026-04-17.1",
            },
          ],
          sensitivity_counts: { mixed: 1 },
          runtime_result_count: 4,
          latest_result_at: "2026-04-17T02:00:00.000Z",
        },
        release_ritual: {
          version: "2026-04-17.1",
          tier_count: 1,
          status: "configured",
        },
        experiment_ledger: {
          version: "2026-04-17.1",
          status: "live",
          required_field_count: 2,
          required_fields: ["benchmark_id", "score"],
          retention: "90d",
          promotion_linkage: "Promotion requires benchmark evidence.",
          evidence_count: 4,
          recent_experiments: [
            {
              id: "routing-proof",
              name: "Routing proof",
              category: "benchmark",
              passed: true,
              score: 0.9,
              max_score: 1,
              timestamp: "2026-04-17T02:00:00.000Z",
            },
          ],
          recent_promotion_events: [],
        },
        deprecation_retirement: {
          version: "2026-04-17.1",
          status: "live",
          asset_class_count: 1,
          asset_classes: ["models"],
          stages: ["active", "retiring"],
          rule: "Retire only after rollback proof.",
        },
        autonomy_activation: {
          version: "2026-04-17.1",
          status: "active",
          activation_state: "full_system_active",
          current_phase_id: "full_system_phase_3",
          current_phase_status: "active",
          current_phase_scope: "full_system",
          phase_count: 3,
          enabled_agent_count: 9,
          allowed_workload_count: 12,
          blocked_workload_count: 0,
          approval_gate_count: 2,
          verified_prerequisite_count: 4,
          prerequisite_count: 4,
          next_phase_id: null,
          next_phase_status: null,
          next_phase_scope: null,
          next_phase_blocker_count: 0,
          next_phase_blocker_ids: [],
          broad_autonomy_enabled: true,
          runtime_mutations_approval_gated: true,
        },
        operator_runbooks: {
          version: "2026-04-17.1",
          runbook_count: 6,
          status: "configured",
        },
      },
    });

    render(<ModelGovernanceCard />, { wrapper: buildWrapper() });

    expect((await screen.findAllByText(/Capability posture/i)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/openai codex/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/foundry coder lane/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/1 degraded/i)).toBeInTheDocument();
  });
});
