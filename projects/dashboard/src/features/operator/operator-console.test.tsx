import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { OperatorConsole } from "./operator-console";

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
        };
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
});
