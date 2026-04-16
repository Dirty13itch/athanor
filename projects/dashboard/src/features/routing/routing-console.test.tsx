import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { RoutingConsole } from "./routing-console";

const { requestJson, postJson, useOperatorSessionStatus, isOperatorSessionLocked } = vi.hoisted(() => ({
  requestJson: vi.fn(),
  postJson: vi.fn(),
  useOperatorSessionStatus: vi.fn(),
  isOperatorSessionLocked: vi.fn(),
}));

vi.mock("@/features/workforce/helpers", () => ({
  postJson,
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

describe("RoutingConsole", () => {
  it("renders the routing feed, provider lanes, and a direct subscriptions handoff for burn posture", async () => {
    useOperatorSessionStatus.mockReturnValue({ isPending: false });
    isOperatorSessionLocked.mockReturnValue(false);

    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/routing/log?limit=30") {
        return {
          entries: [
            {
              task_id: "task-123456789",
              policy_class: "local_only",
              execution_lane: "goose-shell",
              provider: "deepseek",
              outcome: "success",
            },
          ],
        };
      }

      if (url === "/api/routing/providers") {
        return {
          providers: [
            {
              id: "provider-1",
              name: "DeepSeek",
              category: "subscription",
              execution_mode: "local_only",
              status: "healthy",
              tasks_today: 7,
              avg_latency_ms: 380,
              monthly_cost: 0,
            },
          ],
        };
      }

      if (url === "/api/master-atlas") {
        return {
          generated_at: "2026-04-13T15:41:14.068321+00:00",
          turnover_readiness: {
            burn_dispatch_phase_label: "governed_dispatch_shadow",
            provider_gate_state: "completed",
            provider_elasticity_limited: false,
            work_economy_status: "ready",
            self_acceleration_status: "live_compounding_ready",
            capacity_harvest_summary: {
              admission_state: "open_harvest_window",
              harvestable_scheduler_slot_count: 2,
              protected_reserve_slot_count: 2,
              scheduler_queue_depth: 0,
            },
            dispatchable_autonomous_queue_count: 3,
            autonomous_queue_count: 4,
            top_dispatchable_autonomous_task_title: "Dispatch and Work-Economy Closure",
          },
          safe_surface_summary: {
            queue_count: 4,
            dispatchable_queue_count: 3,
            governed_dispatch_status: "claimed",
            governed_current_task_id: "workstream:capacity-and-harvest-truth",
            governed_on_deck_task_id: "workstream:dispatch-and-work-economy-closure",
            current_task_threads: 0,
          },
          autonomous_queue_summary: {
            queue_count: 4,
            dispatchable_queue_count: 3,
            blocked_queue_count: 1,
            top_dispatchable_task_id: "workstream:dispatch-and-work-economy-closure",
            top_dispatchable_title: "Dispatch and Work-Economy Closure",
            top_dispatchable_lane_family: "dispatch_truth_repair",
            governed_dispatch_claim: {
              status: "claimed",
              current_task_id: "workstream:capacity-and-harvest-truth",
              current_task_title: "Capacity and Harvest Truth",
              on_deck_task_id: "workstream:dispatch-and-work-economy-closure",
              on_deck_task_title: "Dispatch and Work-Economy Closure",
              preferred_lane_family: "capacity_truth_repair",
              approved_mutation_class: "auto_harvest",
              approved_mutation_label: "Auto harvest",
              proof_command_or_eval_surface:
                "\"C:\\Program Files\\Python313\\python.exe\" scripts/run_gpu_scheduler_baseline_eval.py",
            },
          },
          governed_dispatch_state: {
            status: "claimed",
            dispatch_outcome: "claimed",
            claim_id: "ralph-claim-123",
            current_task_id: "workstream:dispatch-and-work-economy-closure",
            current_task_title: "Dispatch and Work-Economy Closure",
            on_deck_task_id: "workstream:capacity-and-harvest-truth",
            on_deck_task_title: "Capacity and Harvest Truth",
            preferred_lane_family: "dispatch_truth_repair",
            approved_mutation_label: "Auto harvest",
            proof_command_or_eval_surface:
              "\"C:\\Program Files\\Python313\\python.exe\" scripts/run_ralph_loop_pass.py --skip-refresh",
            queue_count: 4,
            dispatchable_queue_count: 3,
            blocked_queue_count: 1,
            safe_surface_queue_count: 27,
            safe_surface_dispatchable_queue_count: 0,
            recent_dispatch_outcome_count: 0,
            provider_gate_state: "completed",
            work_economy_status: "ready",
            report_path: "reports/truth-inventory/governed-dispatch-state.json",
            materialization: {
              status: "already_materialized",
              backlog_id: "backlog-42",
              backlog_status: "ready",
              report_path: "reports/truth-inventory/governed-dispatch-materialization.json",
            },
          },
          governed_dispatch_execution_report_path: "reports/truth-inventory/governed-dispatch-execution.json",
          governed_dispatch_execution: {
            generated_at: "2026-04-13T21:29:25.338168+00:00",
            source_of_truth: "scripts/run_ralph_loop_pass.py",
            report_path: "reports/truth-inventory/governed-dispatch-execution.json",
            status: "dispatched",
            dispatch_outcome: "success",
            claim_id: "ralph-claim-123",
            current_task_id: "workstream:dispatch-and-work-economy-closure",
            current_task_title: "Dispatch and Work-Economy Closure",
            agent_server_base_url: "http://192.168.1.244:9000",
            backlog_id: "backlog-42",
            backlog_status: "waiting_approval",
            dispatch_path: "/v1/operator/backlog/backlog-42/dispatch",
            dispatch_status_code: 200,
            governor_level: "C",
            governor_reason: "Level C (score=0.48), owner away - deferred",
            error: null,
            task_id: "f884636cc4ac",
            task_status: "pending_approval",
          },
          quota_posture: { record_count: 8, low_confidence_record_count: 2 },
          next_required_approval: {
            label: "No blocked human approval is currently leading the queue",
            reason: "Current routing proof and turnover posture do not expose a higher-priority approval gate.",
            allowed_actions: ["eval_run", "safe_surface_repo_task"],
          },
          lane_recommendations: [
            {
              task_class: "cheap_bulk_transform",
              preferred_lane: "deepseek_cloudsafe_bulk",
              overflow_lane: "responses_background_cloudsafe",
              degraded: false,
            },
            {
              task_class: "repo_wide_audit",
              preferred_lane: "gemini_audit_cloudsafe",
              overflow_lane: "deepseek_cloudsafe_bulk",
              degraded: false,
            },
          ],
        };
      }

      return {};
    });

    render(<RoutingConsole />, { wrapper: buildWrapper() });

    expect(await screen.findByRole("heading", { name: /Routing & Cost/i })).toBeInTheDocument();
    expect(screen.getByText(/Routing spine/i)).toBeInTheDocument();
    expect(screen.getByText(/Execution lanes first, burn second/i)).toBeInTheDocument();
    expect(screen.getByText(/Live compounding posture/i)).toBeInTheDocument();
    expect(screen.getByText(/Dispatch phase/i)).toBeInTheDocument();
    expect((await screen.findAllByText((content) => content.includes("dispatchable of 4 total"))).length).toBeGreaterThan(
      0
    );
    expect((await screen.findAllByText((content) => content.includes("approval held"))).length).toBeGreaterThan(0);
    expect(screen.getByText(/No turnover-critical provider blocker/i)).toBeInTheDocument();
    expect(screen.getByText(/Dispatch posture/i)).toBeInTheDocument();
    expect(screen.getByText(/Harvest admission/i)).toBeInTheDocument();
    expect(screen.getByText(/Open harvest window/i)).toBeInTheDocument();
    expect(screen.getByText(/2 harvestable slots \| 2 reserve-held \| queue depth 0/i)).toBeInTheDocument();
    expect(screen.getByText(/Dispatch runtime/i)).toBeInTheDocument();
    expect(screen.getByText(/Outcome: success/i)).toBeInTheDocument();
    expect(screen.getByText(/Provider gate: completed/i)).toBeInTheDocument();
    expect(screen.getByText(/Work economy: ready/i)).toBeInTheDocument();
    expect(screen.getByText(/3 governed dispatchable of 4 total \| 0 safe-surface dispatchable of 27 total/i)).toBeInTheDocument();
    expect(screen.getByText(/reports\/truth-inventory\/governed-dispatch-state\.json/i)).toBeInTheDocument();
    expect(screen.getByText(/Current governed item/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Capacity and Harvest Truth/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Dispatch and Work-Economy Closure/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/^On deck$/i)).toBeInTheDocument();
    expect(screen.getByText(/Backlog materialization/i)).toBeInTheDocument();
    expect(screen.getByText(/already materialized as backlog-42/i)).toBeInTheDocument();
    expect(screen.getByText(/reports\/truth-inventory\/governed-dispatch-materialization\.json/i)).toBeInTheDocument();
    expect(screen.getByText(/Execution handoff/i)).toBeInTheDocument();
    expect(screen.getByText(/dispatched for backlog-42/i)).toBeInTheDocument();
    expect(screen.getByText(/success \| task f884636cc4ac \(pending approval\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Governor C \| Level C \(score=0\.48\), owner away - deferred/i)).toBeInTheDocument();
    expect(screen.getByText(/reports\/truth-inventory\/governed-dispatch-execution\.json/i)).toBeInTheDocument();
    expect(screen.getByText(/Proof surface/i)).toBeInTheDocument();
    expect(screen.getByText(/"C:\\Program Files\\Python313\\python\.exe" scripts\/run_ralph_loop_pass\.py --skip-refresh/i)).toBeInTheDocument();
    expect(screen.getByText(/Recommended lane chain/i)).toBeInTheDocument();
    expect(screen.getByText(/Approval posture/i)).toBeInTheDocument();
    expect(screen.getByText(/Allowed now: eval run/i)).toBeInTheDocument();
    expect(screen.getAllByText(/safe surface repo task/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Recent decisions/i)).toBeInTheDocument();
    expect(screen.getByText(/Lane posture/i)).toBeInTheDocument();
    expect(screen.getByText(/Active providers/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Materialize in Backlog/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Execution Recorded/i })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Open Backlog/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /Open Backlog/i })[0]).toHaveAttribute(
      "href",
      "/backlog?status=all"
    );
    expect(screen.getAllByRole("link", { name: /Open Subscriptions/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /Open Operator/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /Open Topology/i }).length).toBeGreaterThan(0);
    expect(screen.getByText(/Spend, leases, and handoffs live there\./i)).toBeInTheDocument();
    expect(await screen.findByText(/goose-shell/i)).toBeInTheDocument();
    expect((await screen.findAllByText("DeepSeek")).length).toBeGreaterThan(0);
  });
});
