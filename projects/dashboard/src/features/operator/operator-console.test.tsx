import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { OperatorConsole } from "./operator-console";

const pilotReadinessPayload = {
  generatedAt: "2026-04-16T15:11:19.861884+00:00",
  available: true,
  degraded: false,
  detail: null,
  sourceKind: "workspace_generated_atlas" as const,
  sourcePath: "/mnt/c/Athanor/projects/dashboard/src/generated/master-atlas.json",
  summary: {
    total: 3,
    formalEvalComplete: 0,
    formalEvalFailed: 0,
    manualReviewPending: 0,
    readyForFormalEval: 0,
    operatorSmokeOnly: 0,
    scaffoldOnly: 0,
    blocked: 3,
  },
  records: [
    {
      capabilityId: "letta-memory-plane",
      label: "Letta Memory Plane",
      laneStatus: null,
      capabilityStage: null,
      hostId: "desk",
      readinessState: "blocked",
      proofTier: "operator_smoke_plus_formal_scaffold",
      blockingReasons: ["missing_packet", "missing_env:LETTA_API_KEY"],
      commandChecks: [],
      packetPath: "C:/athanor-devstack/docs/promotion-packets/letta-memory-plane.md",
      latestEvalRunId: null,
      latestEvalStatus: null,
      latestEvalOutcome: null,
      latestEvalAt: null,
      formalEvalStatus: null,
      formalEvalAt: null,
      formalEvalDecisionReason: null,
      formalEvalPrimaryFailureHint: null,
      formalPreflightStatus: null,
      formalPreflightAt: null,
      formalPreflightBlockerClass: "env_wiring",
      formalPreflightBlockingReasons: ["missing_env:LETTA_API_KEY"],
      formalPreflightMissingCommands: [],
      formalPreflightMissingEnvVars: ["LETTA_API_KEY"],
      formalPreflightMissingFixtureFiles: [],
      formalPreflightMissingResultFiles: [],
      manualReviewOutcome: null,
      manualReviewSummary: null,
      nextAction: "Wire LETTA_API_KEY, run the bounded continuity benchmark, and keep replayability and pruning explicit.",
      nextFormalGate: "Wire the required formal-eval env vars: `LETTA_API_KEY`.",
      formalRunnerSupport: null,
    },
    {
      capabilityId: "openhands-bounded-worker-lane",
      label: "OpenHands Bounded Worker Lane",
      laneStatus: null,
      capabilityStage: null,
      hostId: "desk",
      readinessState: "blocked",
      proofTier: "blocked",
      blockingReasons: [
        "missing_command:openhands",
        "missing_packet",
        "missing_env:OPENAI_API_KEY",
        "missing_env:PROMPTFOO_OPENHANDS_CMD",
        "missing_env:PROMPTFOO_OPENHANDS_ARGS_JSON",
      ],
      commandChecks: [],
      packetPath: "C:/athanor-devstack/docs/promotion-packets/openhands-bounded-worker-lane.md",
      latestEvalRunId: null,
      latestEvalStatus: null,
      latestEvalOutcome: null,
      latestEvalAt: null,
      formalEvalStatus: null,
      formalEvalAt: null,
      formalEvalDecisionReason: null,
      formalEvalPrimaryFailureHint: null,
      formalPreflightStatus: null,
      formalPreflightAt: null,
      formalPreflightBlockerClass: "missing_command",
      formalPreflightBlockingReasons: ["missing_command:openhands"],
      formalPreflightMissingCommands: ["openhands"],
      formalPreflightMissingEnvVars: ["OPENAI_API_KEY"],
      formalPreflightMissingFixtureFiles: [],
      formalPreflightMissingResultFiles: [],
      manualReviewOutcome: null,
      manualReviewSummary: null,
      nextAction: "Expose the OpenHands command on DESK, clear the worker env wiring, and run the bounded-worker eval.",
      nextFormalGate: "Install or expose `openhands` on the preferred pilot host.",
      formalRunnerSupport: null,
    },
    {
      capabilityId: "agent-governance-toolkit-policy-plane",
      label: "Agent Governance Toolkit Policy Plane",
      laneStatus: null,
      capabilityStage: null,
      hostId: "desk",
      readinessState: "blocked",
      proofTier: "formal_eval_failed",
      blockingReasons: ["missing_packet"],
      commandChecks: [],
      packetPath: "C:/athanor-devstack/docs/promotion-packets/agent-governance-toolkit-policy-plane.md",
      latestEvalRunId: null,
      latestEvalStatus: null,
      latestEvalOutcome: null,
      latestEvalAt: null,
      formalEvalStatus: "failed",
      formalEvalAt: null,
      formalEvalDecisionReason: null,
      formalEvalPrimaryFailureHint: null,
      formalPreflightStatus: null,
      formalPreflightAt: null,
      formalPreflightBlockerClass: null,
      formalPreflightBlockingReasons: [],
      formalPreflightMissingCommands: [],
      formalPreflightMissingEnvVars: [],
      formalPreflightMissingFixtureFiles: [],
      formalPreflightMissingResultFiles: [],
      manualReviewOutcome: "rejected_as_redundant_for_current_stack",
      manualReviewSummary: "Current narrow approval-held mutation bundle does not prove non-duplicative operational value.",
      nextAction: "Leave this lane below adapter work on the current manual review, and only reopen it if a second protocol-boundary scenario proves unique value over native Athanor policy.",
      nextFormalGate: "Keep this lane below adapter work unless a second protocol-boundary scenario shows non-duplicative value over native Athanor policy.",
      formalRunnerSupport: null,
    },
  ],
};

vi.mock("@/generated/master-atlas.json", () => ({
  default: {
    capability_pilot_readiness: {
      generated_at: "2026-04-16T15:11:19.861884+00:00",
      records: [
        {
          capability_id: "letta-memory-plane",
          label: "Letta Memory Plane",
          readiness_state: "blocked",
          blocking_reasons: ["missing_packet", "missing_env:LETTA_API_KEY"],
          next_action: "Wire LETTA_API_KEY, run the bounded continuity benchmark, and keep replayability and pruning explicit.",
          next_formal_gate: "Wire the required formal-eval env vars: `LETTA_API_KEY`.",
          proof_tier: "operator_smoke_plus_formal_scaffold",
        },
        {
          capability_id: "openhands-bounded-worker-lane",
          label: "OpenHands Bounded Worker Lane",
          readiness_state: "blocked",
          blocking_reasons: [
            "missing_command:openhands",
            "missing_packet",
            "missing_env:OPENAI_API_KEY",
            "missing_env:PROMPTFOO_OPENHANDS_CMD",
            "missing_env:PROMPTFOO_OPENHANDS_ARGS_JSON",
          ],
          next_action: "Expose the OpenHands command on DESK, clear the worker env wiring, and run the bounded-worker eval.",
          next_formal_gate: "Install or expose `openhands` on the preferred pilot host.",
          proof_tier: "blocked",
        },
        {
          capability_id: "agent-governance-toolkit-policy-plane",
          label: "Agent Governance Toolkit Policy Plane",
          readiness_state: "blocked",
          blocking_reasons: ["missing_packet"],
          next_action: "Leave this lane below adapter work on the current manual review, and only reopen it if a second protocol-boundary scenario proves unique value over native Athanor policy.",
          next_formal_gate: "Keep this lane below adapter work unless a second protocol-boundary scenario shows non-duplicative value over native Athanor policy.",
          proof_tier: "formal_eval_failed",
          manual_review_outcome: "rejected_as_redundant_for_current_stack",
        },
      ],
    },
  },
}));

const { requestJson, postWithoutBody, postJson } = vi.hoisted(() => ({
  requestJson: vi.fn(),
  postWithoutBody: vi.fn(),
  postJson: vi.fn(),
}));

vi.mock("@/features/workforce/helpers", () => ({
  requestJson,
  postWithoutBody,
  postJson,
}));

vi.mock("@/lib/sse", () => ({
  readChatEventStream: vi.fn(),
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

describe("OperatorConsole", () => {
  it("renders the operator route as a decision desk with governance posture and explicit links to the owning routes", async () => {
    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/operator/approvals?status=pending") {
        return {
          approvals: [
            {
              id: "approval-1",
              requested_action: "promote",
              privilege_class: "release-tier",
              reason: "Advance GPU scheduler packet.",
              task_prompt: "Advance GPU scheduler packet after verifying the rollout evidence.",
              task_agent_id: "scheduler",
              task_priority: "high",
              requested_at: 1_710_000_000,
            },
          ],
        };
      }

      if (url === "/api/operator/governance") {
        return {
          current_mode: {
            mode: "constrained",
            trigger: "provider gate",
            entered_at: 1_710_000_000,
          },
          launch_blockers: ["provider_gate_blocked"],
          launch_ready: false,
          attention_posture: {
            recommended_mode: "constrained",
            breaches: ["provider elasticity limited"],
          },
        };
      }

      if (url === "/api/operator/summary") {
        return {
          tasks: {
            pending_approval: 1,
            failed_actionable: 2,
            stale_lease: 1,
            stale_lease_actionable: 1,
            stale_lease_recovered_historical: 2,
            failed_historical_repaired: 3,
          },
          builderFrontDoor: {
            available: true,
            degraded: false,
            detail: null,
            updated_at: "2026-04-17T00:00:00.000Z",
            session_count: 1,
            active_count: 1,
            pending_approval_count: 1,
            recent_artifact_count: 0,
            current_session: {
              id: "builder-1",
              title: "Implement the first builder route",
              status: "waiting_approval",
              primary_adapter: "codex",
              current_route: "Codex direct implementation",
              verification_status: "planned",
              pending_approval_count: 1,
              artifact_count: 0,
              resumable_handle: null,
              shadow_mode: false,
              fallback_state: "approval_pending",
              updated_at: "2026-04-17T00:00:00.000Z",
            },
            sessions: [],
          },
          steadyState: {
            closureState: "repo_safe_complete",
            operatorMode: "steady_state_monitoring",
            interventionLabel: "No action needed",
            interventionLevel: "ambient",
            interventionSummary: "Queue is moving without operator intervention.",
            needsYou: false,
            nextOperatorAction: "Monitor the next governed handoff and only intervene when approvals appear.",
            queueDispatchable: 4,
            queueTotal: 7,
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
          },
        };
      }

      if (url === "/api/operator/pilot-readiness") {
        return pilotReadinessPayload;
      }

      if (url === "/api/master-atlas") {
        return {
          generated_at: "2026-04-13T08:01:42.197539+00:00",
          governed_dispatch_execution: {
            generated_at: "2026-04-13T21:57:17.698187+00:00",
            status: "already_dispatched",
            dispatch_outcome: "claimed",
            current_task_title: "Dispatch and Work-Economy Closure",
            backlog_status: "scheduled",
            governor_level: "A",
            task_status: "running",
            report_path: "reports/truth-inventory/governed-dispatch-execution.json",
          },
          governed_dispatch_execution_report_path:
            "reports/truth-inventory/governed-dispatch-execution.json",
          goose_evidence_summary: {
            capability_id: "goose-operator-shell",
            label: "Goose Operator Shell",
            readiness_state: "formal_eval_complete",
            formal_eval_status: "passed",
            formal_eval_at: "2026-04-12T08:44:35.466323+00:00",
            formal_eval_successes: 8,
            formal_eval_failures: 0,
            formal_eval_errors: 0,
            formal_eval_duration_ms: 129709,
            operator_test_status: "live_partial",
            request_surface_hint: "dashboard-routed bounded shell task",
            next_action: "Advance this lane into packet review, promotion, or explicit bounded retention.",
            next_formal_gate: "Formal eval is complete; move this lane to promotion or bounded retention decision.",
            packet_path: "C:/athanor-devstack/docs/promotion-packets/goose-operator-shell.md",
            packet_status: "ready_for_review",
            approval_state: "operator_review_required_before_adoption",
            proof_state: "evidence_only",
            source_safe_remaining: [
              "Capture representative dashboard-routed shell evidence plus the explicit MCP allowlist and failure fallback proof before widening Goose beyond shadow-tier review.",
            ],
            approval_gated_remaining: [
              "Approve the DESK Goose operator-shell rollout packet before changing the preferred shell helper or local Goose runtime defaults.",
            ],
            command: "goose",
            command_available_locally: true,
            command_inventory_status: "installed",
            command_inventory_version: "1.30.0",
            command_local_path: "C:\\Users\\Shaun\\.local\\bin\\goose.EXE",
            wrapper_mode: "goose_wrapped",
          },
          turnover_readiness: {
            burn_dispatch_phase_label: "governed_dispatch_shadow",
            provider_gate_state: "completed",
            work_economy_status: "ready",
            autonomous_queue_count: 4,
            dispatchable_autonomous_queue_count: 4,
            top_dispatchable_autonomous_task_title: "Dispatch and Work-Economy Closure",
          },
          autonomous_queue_summary: {
            queue_count: 4,
            dispatchable_queue_count: 4,
            blocked_queue_count: 0,
            top_dispatchable_title: "Dispatch and Work-Economy Closure",
            top_dispatchable_lane_family: "dispatch_truth_repair",
          },
          safe_surface_summary: {
            queue_count: 27,
            dispatchable_queue_count: 0,
            blocked_queue_count: 16,
            on_deck_task_id: "watch-refresh-foundry-remote-verification-baseline",
          },
          next_required_approval: null,
        };
      }

      return {};
    });

    render(<OperatorConsole />, { wrapper: buildWrapper() });

    expect(await screen.findByRole("heading", { name: /Operator Console/i })).toBeInTheDocument();
    expect(screen.getByText(/Decision queue/i)).toBeInTheDocument();
    expect(screen.getByText(/Current guardrails/i)).toBeInTheDocument();
    expect(screen.getByText(/Keep this page as a command desk/i)).toBeInTheDocument();
    expect(screen.getByText(/Direct command lane/i)).toBeInTheDocument();
    expect(await screen.findByText(/Governed dispatch handoff/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Dispatch and Work-Economy Closure/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/current governed handoff/i)).toBeInTheDocument();
    expect(screen.getAllByText(/No action needed/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/workspace report/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Cheap Bulk Cloud/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Builder front door/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /Open Builder/i })).toBeInTheDocument();
    expect(await screen.findByText(/Pilot readiness/i)).toBeInTheDocument();
    expect((await screen.findAllByText(/Letta Memory Plane/i)).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/OpenHands Bounded Worker Lane/i)).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/Agent Governance Toolkit Policy Plane/i)).length).toBeGreaterThan(0);
    expect(await screen.findByText(/Advance GPU scheduler packet after verifying the rollout evidence\./i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Routing/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Topology/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Governor/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Approve/i })).toBeInTheDocument();
  });

  it("shows a degraded operator-feed notice instead of implying the queue is clear", async () => {
    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/operator/approvals?status=pending") {
        return {
          available: false,
          degraded: true,
          approvals: [],
          count: 0,
        };
      }

      if (url === "/api/operator/governance") {
        return {
          available: false,
          degraded: true,
          current_mode: { mode: "feed_unavailable" },
          launch_blockers: ["operator_upstream_unavailable"],
          launch_ready: false,
          attention_posture: {
            recommended_mode: "manual_review",
            breaches: ["Operator governance feed is temporarily unavailable."],
          },
        };
      }

      if (url === "/api/operator/summary") {
        return {
          available: false,
          degraded: true,
          tasks: {
            pending_approval: 0,
            failed_actionable: 0,
            stale_lease: 0,
            stale_lease_actionable: 0,
            stale_lease_recovered_historical: 0,
            failed_historical_repaired: 0,
          },
        };
      }

      if (url === "/api/operator/pilot-readiness") {
        return {
          ...pilotReadinessPayload,
          available: false,
          degraded: true,
          detail: "Capability pilot readiness feed is unavailable.",
        };
      }

      return {};
    });

    render(<OperatorConsole />, { wrapper: buildWrapper() });

    expect(await screen.findByText(/Operator data degraded/i)).toBeInTheDocument();
    expect(screen.getByText(/Approval feed unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText(/Queue clear/i)).not.toBeInTheDocument();
  });

  it("shows a degraded context notice when the master atlas feed is degraded", async () => {
    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/operator/approvals?status=pending") {
        return { approvals: [], count: 0 };
      }

      if (url === "/api/operator/governance") {
        return {
          current_mode: { mode: "normal", entered_at: 1_710_000_000 },
          launch_blockers: [],
          launch_ready: true,
          attention_posture: { recommended_mode: "normal", breaches: [] },
        };
      }

      if (url === "/api/operator/summary") {
        return {
          tasks: {
            pending_approval: 0,
            failed_actionable: 0,
            stale_lease: 0,
            stale_lease_actionable: 0,
            stale_lease_recovered_historical: 0,
            failed_historical_repaired: 0,
          },
        };
      }

      if (url === "/api/operator/pilot-readiness") {
        return pilotReadinessPayload;
      }

      if (url === "/api/master-atlas") {
        return {
          generated_at: "2026-04-13T08:05:00.000000+00:00",
          available: false,
          degraded: true,
          detail: "Master atlas feed is temporarily unavailable from this dashboard runtime.",
          error: "Master atlas feed is unavailable",
          turnover_readiness: {
            burn_dispatch_phase_label: "unknown",
            provider_gate_state: "unknown",
            work_economy_status: "unknown",
            autonomous_queue_count: 0,
            dispatchable_autonomous_queue_count: 0,
            top_dispatchable_autonomous_task_title: null,
          },
          autonomous_queue_summary: {
            queue_count: 0,
            dispatchable_queue_count: 0,
            blocked_queue_count: 0,
            top_dispatchable_title: null,
            top_dispatchable_lane_family: null,
          },
          safe_surface_summary: {
            queue_count: 0,
            dispatchable_queue_count: 0,
            blocked_queue_count: 0,
            on_deck_task_id: null,
          },
          next_required_approval: null,
        };
      }

      return {};
    });

    render(<OperatorConsole />, { wrapper: buildWrapper() });

    expect((await screen.findAllByText(/Dispatch map degraded/i)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/dashboard runtime/i).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /Open Routing/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /Open Topology/i }).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Dispatch map unavailable/i)).not.toBeInTheDocument();
  });

  it("shows a dedicated steady-state front door degraded notice when operator feeds are otherwise available", async () => {
    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/operator/approvals?status=pending") {
        return { approvals: [] };
      }

      if (url === "/api/operator/governance") {
        return {
          current_mode: { mode: "steady_state_monitoring" },
          launch_blockers: [],
          launch_ready: true,
          attention_posture: { recommended_mode: "steady_state_monitoring", breaches: [] },
        };
      }

      if (url === "/api/operator/summary") {
        return {
          tasks: {
            pending_approval: 0,
            failed_actionable: 0,
            stale_lease: 0,
            stale_lease_actionable: 0,
            stale_lease_recovered_historical: 0,
            failed_historical_repaired: 0,
          },
          steadyState: null,
          steadyStateStatus: {
            available: false,
            degraded: true,
            detail: "Invalid steady-state front door at /tmp/steady-state-status.json",
            sourceKind: "workspace_report",
            sourcePath: "/tmp/steady-state-status.json",
          },
        };
      }

      if (url === "/api/operator/pilot-readiness") {
        return pilotReadinessPayload;
      }

      if (url === "/api/master-atlas") {
        return { generated_at: "2026-04-13T08:01:42.197539+00:00" };
      }

      return {};
    });

    render(<OperatorConsole />, { wrapper: buildWrapper() });

    expect(await screen.findByText(/Steady-state front door degraded/i)).toBeInTheDocument();
    expect(screen.getByText(/Invalid steady-state front door at \/tmp\/steady-state-status.json/i)).toBeInTheDocument();
    expect(screen.getByText(/Source: workspace_report/i)).toBeInTheDocument();
  });
});
