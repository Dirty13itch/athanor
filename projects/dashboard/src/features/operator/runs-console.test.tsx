import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { RunsConsole } from "./runs-console";

const { requestJson } = vi.hoisted(() => ({
  requestJson: vi.fn(),
}));

vi.mock("@/features/workforce/helpers", () => ({
  requestJson,
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

describe("RunsConsole", () => {
  it("renders a degraded runs surface when the upstream feed is unavailable", async () => {
    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/operator/runs?status=running") {
        return {
          available: false,
          degraded: true,
          runs: [],
          count: 0,
        };
      }

      if (url === "/api/operator/summary") {
        return {};
      }

      if (url === "/api/operator/runs?limit=500") {
        return {
          available: false,
          degraded: true,
          runs: [],
          count: 0,
        };
      }

      if (url === "/api/execution/reviews?status=pending") {
        return {
          reviews: [],
          count: 0,
        };
      }

      if (url === "/api/execution/results?limit=500") {
        return {
          results: [],
          count: 0,
        };
      }

      return {};
    });

    render(<RunsConsole />, { wrapper: buildWrapper() });

    expect(await screen.findByRole("heading", { name: "Runs", level: 1 })).toBeInTheDocument();
    expect(await screen.findByText(/Runs feed degraded/i)).toBeInTheDocument();
    expect(screen.getByText(/Runs feed unavailable/i)).toBeInTheDocument();
  });

  it("uses shared execution review and result evidence for run pressure", async () => {
    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/operator/runs?status=running") {
        return {
          available: true,
          degraded: false,
          runs: [
            {
              id: "bootstrap-run-1",
              task_id: "slice-1",
              backlog_id: "backlog-1",
              agent_id: "bootstrap-supervisor",
              workload_class: "bootstrap_takeover",
              provider_lane: "bootstrap_supervisor",
              runtime_lane: "repo_worktree",
              policy_class: "private",
              status: "running",
              summary: "Bootstrap cutover is running.",
              created_at: 100,
              updated_at: 150,
              completed_at: 0,
              step_count: 3,
              approval_pending: false,
              latest_attempt: {
                id: "bootstrap-run-1-attempt",
                runtime_host: "bootstrap-supervisor",
                status: "running",
                heartbeat_at: 150,
              },
            },
          ],
          count: 1,
        };
      }

      if (url === "/api/operator/runs?limit=500") {
        return {
          available: true,
          degraded: false,
          runs: [
            {
              id: "builder-run-1",
              task_id: "builder-1",
              backlog_id: "backlog-1",
              agent_id: "codex",
              workload_class: "multi_file_implementation",
              provider_lane: "openai_codex",
              runtime_lane: "codex",
              policy_class: "private_but_cloud_allowed",
              status: "waiting_approval",
              summary: "Builder route is waiting.",
              created_at: 100,
              updated_at: 200,
              completed_at: 0,
              step_count: 4,
              approval_pending: true,
              latest_attempt: {
                id: "builder-run-1-attempt",
                runtime_host: "codex-cloud",
                status: "waiting_approval",
                heartbeat_at: 200,
              },
            },
            {
              id: "builder-run-2",
              task_id: "builder-2",
              backlog_id: "backlog-2",
              agent_id: "codex",
              workload_class: "multi_file_implementation",
              provider_lane: "openai_codex",
              runtime_lane: "codex",
              policy_class: "private_but_cloud_allowed",
              status: "failed",
              summary: "Builder route failed verification.",
              created_at: 110,
              updated_at: 210,
              completed_at: 210,
              step_count: 5,
              approval_pending: false,
              latest_attempt: {
                id: "builder-run-2-attempt",
                runtime_host: "codex-cloud",
                status: "failed",
                heartbeat_at: 210,
              },
            },
            {
              id: "bootstrap-run-1",
              task_id: "slice-1",
              backlog_id: "backlog-1",
              agent_id: "bootstrap-supervisor",
              workload_class: "bootstrap_takeover",
              provider_lane: "bootstrap_supervisor",
              runtime_lane: "repo_worktree",
              policy_class: "private",
              status: "running",
              summary: "Bootstrap cutover is running.",
              created_at: 100,
              updated_at: 150,
              completed_at: 0,
              step_count: 3,
              approval_pending: false,
              latest_attempt: {
                id: "bootstrap-run-1-attempt",
                runtime_host: "bootstrap-supervisor",
                status: "running",
                heartbeat_at: 150,
              },
            },
          ],
          count: 3,
        };
      }

      if (url === "/api/execution/reviews?status=pending") {
        return {
          reviews: [
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
              requested_at: 200,
              task_prompt: "Implement the first builder route",
              task_agent_id: "codex",
              task_priority: "high",
              task_status: "pending_approval",
              deep_link: "/review?selection=builder-review-1",
              metadata: {},
            },
          ],
          count: 1,
        };
      }

      if (url === "/api/execution/results?limit=500") {
        return {
          results: [
            {
              id: "builder-result:builder-2",
              family: "builder",
              source: "builder_front_door",
              owner_kind: "session",
              owner_id: "builder-2",
              related_run_id: "builder-run-2",
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
              updated_at: "2026-04-18T16:00:00.000Z",
              deep_link: "/builder?session=builder-2",
              metadata: {},
            },
          ],
          count: 1,
        };
      }

      return {};
    });

    render(<RunsConsole />, { wrapper: buildWrapper() });

    expect((await screen.findAllByText(/Kernel-backed approval holds linked to execution runs\./i)).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Shared reviews").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Result alerts").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Kernel-backed failed, blocked, or cancelled result packets\./i).length).toBeGreaterThanOrEqual(1);
    expect(requestJson).toHaveBeenCalledWith("/api/operator/runs?limit=500");
    expect(requestJson).toHaveBeenCalledWith("/api/execution/reviews?status=pending");
    expect(requestJson).toHaveBeenCalledWith("/api/execution/results?limit=500");
  });
});
