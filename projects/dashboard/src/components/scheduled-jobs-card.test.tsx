import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ScheduledJobsCard } from "./scheduled-jobs-card";

const { getScheduledJobs } = vi.hoisted(() => ({
  getScheduledJobs: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  getOperatorScheduledJobs: getScheduledJobs,
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

afterEach(() => {
  getScheduledJobs.mockReset();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ScheduledJobsCard", () => {
  it("renders queue-backed and direct scheduled jobs distinctly", async () => {
    getScheduledJobs.mockResolvedValue({
      jobs: [
        {
          id: "agent-schedule:coding-agent",
          job_family: "agent_schedule",
          title: "Coding queue sweep",
          cadence: "every 30m",
          trigger_mode: "interval",
          last_run: "2026-03-11T18:10:00Z",
          next_run: "2026-03-11T18:40:00Z",
          current_state: "scheduled",
          last_outcome: "materialized_to_backlog",
          owner_agent: "coding-agent",
          deep_link: "/workforce",
          control_scope: "scheduler",
          paused: false,
          can_run_now: true,
          can_override_now: true,
          last_summary: "Latest coding-agent schedule emitted canonical builder queue work.",
          last_error: null,
          last_backlog_id: "backlog-coding-1",
          last_execution_mode: "materialized_to_backlog",
          last_execution_plane: "queue",
          last_admission_classification: "queue",
          last_admission_reason: "Scheduled product work is routed into the canonical backlog queue.",
          last_materialization_status: "created",
        },
        {
          id: "daily-digest",
          job_family: "daily_digest",
          title: "Daily briefing",
          cadence: "daily 6:55",
          trigger_mode: "daily",
          last_run: "2026-03-11T06:55:00Z",
          next_run: "2026-03-12T06:55:00Z",
          current_state: "scheduled",
          last_outcome: "scheduled",
          owner_agent: "system",
          deep_link: "/",
          control_scope: "scheduler",
          paused: false,
          can_run_now: true,
          last_summary: "Daily briefing cadence is healthy.",
          last_error: null,
          last_backlog_id: null,
          last_execution_mode: "executed_directly",
          last_execution_plane: "direct_control",
          last_admission_classification: "direct_control",
          last_admission_reason: "This loop remains a direct control-plane routine in v1.",
          last_materialization_status: null,
        },
      ],
      count: 2,
    });

    render(<ScheduledJobsCard />, { wrapper: buildWrapper() });

    expect(await screen.findByText("Coding queue sweep")).toBeInTheDocument();
    expect(screen.getByText("Daily briefing")).toBeInTheDocument();
    expect(screen.getByText("backlog-coding-1")).toBeInTheDocument();
    expect(screen.getByText("created")).toBeInTheDocument();
    expect(screen.getAllByText("queue-backed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("direct").length).toBeGreaterThan(0);
  });

  it("surfaces backlog materialization feedback when a queue-backed job is run", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        job_id: "agent-schedule:coding-agent",
        status: "materialized_to_backlog",
        backlog_id: "backlog-coding-manual",
        materialization_status: "created",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const payload = {
      jobs: [
        {
          id: "agent-schedule:coding-agent",
          job_family: "agent_schedule",
          title: "Coding queue sweep",
          cadence: "every 30m",
          trigger_mode: "interval",
          last_run: "2026-03-11T18:10:00Z",
          next_run: "2026-03-11T18:40:00Z",
          current_state: "scheduled",
          last_outcome: "materialized_to_backlog",
          owner_agent: "coding-agent",
          deep_link: "/workforce",
          control_scope: "scheduler",
          paused: false,
          can_run_now: true,
          can_override_now: true,
          last_summary: "Latest coding-agent schedule emitted canonical builder queue work.",
          last_error: null,
          last_backlog_id: "backlog-coding-1",
          last_execution_mode: "materialized_to_backlog",
          last_execution_plane: "queue",
          last_admission_classification: "queue",
          last_admission_reason: "Scheduled product work is routed into the canonical backlog queue.",
          last_materialization_status: "created",
        },
      ],
      count: 1,
    };
    getScheduledJobs.mockResolvedValueOnce(payload).mockResolvedValueOnce(payload);

    const user = userEvent.setup();
    render(<ScheduledJobsCard />, { wrapper: buildWrapper() });

    const [runNowButton] = await screen.findAllByRole("button", { name: "Run now" });
    await user.click(runNowButton);

    await waitFor(() => {
      expect(
        screen.getByText(
          "Scheduled job agent-schedule:coding-agent materialized to backlog backlog-coding-manual (created).",
        ),
      ).toBeInTheDocument();
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/operator/scheduled/agent-schedule%3Acoding-agent/run",
      expect.objectContaining({
        method: "POST",
      }),
    );
  });

  it("renders proposal-only and blocked scheduled posture honestly", async () => {
    getScheduledJobs.mockResolvedValue({
      jobs: [
        {
          id: "improvement-cycle",
          job_family: "improvement_cycle",
          title: "Improvement cycle",
          cadence: "daily 5:30",
          trigger_mode: "daily",
          last_run: "2026-03-11T05:30:00Z",
          next_run: "2026-03-12T05:30:00Z",
          current_state: "scheduled",
          last_outcome: "blocked_by_review_debt",
          owner_agent: "system",
          deep_link: "/review",
          control_scope: "scheduler",
          paused: false,
          can_run_now: true,
          can_override_now: true,
          last_summary: "Improvement cycle deferred: pending review debt must clear first.",
          last_error: null,
          last_backlog_id: null,
          last_execution_mode: "executed_directly",
          last_execution_plane: "proposal_only",
          last_admission_classification: "blocked_by_review_debt",
          last_admission_reason: "Pending review debt must clear first.",
          last_materialization_status: null,
        },
      ],
      count: 1,
    });

    render(<ScheduledJobsCard />, { wrapper: buildWrapper() });

    expect(await screen.findByText("Improvement cycle")).toBeInTheDocument();
    expect(screen.getByText("proposal-only")).toBeInTheDocument();
    expect(screen.getAllByText("blocked by review debt").length).toBeGreaterThan(0);
    expect(screen.getByText(/Improvement cycle deferred: pending review debt must clear first\./i)).toBeInTheDocument();
  });
});
