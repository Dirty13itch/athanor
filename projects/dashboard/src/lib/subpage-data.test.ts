import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getFixtureOverviewSnapshot, getFixtureWorkforceSnapshot } from "@/lib/dashboard-fixtures";

const { getProjectsSnapshot, getWorkforceSnapshot, loadExecutionReviews, loadExecutionResults } = vi.hoisted(() => ({
  getProjectsSnapshot: vi.fn(),
  getWorkforceSnapshot: vi.fn(),
  loadExecutionReviews: vi.fn(),
  loadExecutionResults: vi.fn(),
}));

vi.mock("@/lib/dashboard-data", () => ({
  getProjectsSnapshot,
  getWorkforceSnapshot,
}));

vi.mock("@/lib/executive-kernel", () => ({
  loadExecutionReviews,
  loadExecutionResults,
}));

import { getHistorySnapshot, getIntelligenceSnapshot, getReviewSnapshot } from "./subpage-data";

function buildWorkforceSnapshot() {
  const fixture = getFixtureWorkforceSnapshot();
  const livePending = {
    ...fixture.tasks[0]!,
    id: "task-live-review",
    prompt: "Approve the live review-backed runtime packet.",
    status: "pending_approval" as const,
    reviewId: "approval:task-live-review",
  };
  const stalePending = {
    ...fixture.tasks[1]!,
    id: "task-stale-review",
    agentId: "creative-agent",
    prompt: "Pending approval without a shared review object.",
    status: "pending_approval" as const,
    reviewId: null,
  };
  const failedTask = {
    ...fixture.tasks[7]!,
    id: "task-failed-review",
    agentId: "media-agent",
    prompt: "Review the current Sonarr queue after the failed import pass.",
    status: "failed" as const,
    reviewId: null,
    resultId: null,
  };
  const completedFileTask = {
    ...fixture.tasks[5]!,
    id: "task-completed-review",
    agentId: "coding-agent",
    prompt: "Write the renderer diff summary and attach the file artifact.",
    status: "completed" as const,
    reviewId: null,
    resultId: null,
  };
  const staleFailedTask = {
    ...fixture.tasks[7]!,
    id: "task-stale-failed-review",
    agentId: "media-agent",
    prompt: "Failed media task without a shared execution result.",
    status: "failed" as const,
    reviewId: null,
    resultId: null,
  };
  const staleCompletedFileTask = {
    ...fixture.tasks[5]!,
    id: "task-stale-completed-review",
    agentId: "coding-agent",
    prompt: "Write the stale renderer diff without a shared execution result.",
    status: "completed" as const,
    reviewId: null,
    resultId: null,
  };

  return {
    ...fixture,
    tasks: [livePending, stalePending, failedTask, staleFailedTask, completedFileTask, staleCompletedFileTask],
  };
}

function mockAgentFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/v1/activity?limit=60")) {
        return new Response(
          JSON.stringify({
            activity: [
              {
                agent: "coding-agent",
                action_type: "approve_packet",
                input_summary: "Approve the live review-backed runtime packet.",
                output_summary: "Waiting on operator review.",
                tools_used: ["run_command"],
                duration_ms: 42,
                timestamp: "2026-04-18T08:45:00.000Z",
              },
              {
                agent: "creative-agent",
                action_type: "stale_review",
                input_summary: "Pending approval without a shared review object.",
                output_summary: "Task still says pending approval.",
                tools_used: ["generate_image"],
                duration_ms: 18,
                timestamp: "2026-04-18T08:40:00.000Z",
              },
              {
                agent: "media-agent",
                action_type: "failed_review",
                input_summary: "Review the current Sonarr queue after the failed import pass.",
                output_summary: "Queue inspection failed and needs result-backed review.",
                tools_used: ["fetch_queue"],
                duration_ms: 31,
                timestamp: "2026-04-18T08:35:00.000Z",
              },
              {
                agent: "media-agent",
                action_type: "stale_failed_review",
                input_summary: "Failed media task without a shared execution result.",
                output_summary: "Task status alone should not create a review item.",
                tools_used: ["fetch_queue"],
                duration_ms: 19,
                timestamp: "2026-04-18T08:32:00.000Z",
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }

      if (url.includes("/v1/conversations?limit=40")) {
        return new Response(JSON.stringify({ conversations: [] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }

      if (url.endsWith("/v1/outputs")) {
        return new Response(JSON.stringify({ outputs: [] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }

      if (url.includes("/v1/patterns")) {
        return new Response(
          JSON.stringify({
            timestamp: "2026-04-18T09:00:00.000Z",
            period_hours: 24,
            event_count: 0,
            activity_count: 0,
            patterns: [],
            recommendations: [],
            autonomy_adjustments: [],
            agent_behavioral_patterns: {},
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }

      if (url.includes("/v1/learning/metrics")) {
        return new Response(
          JSON.stringify({
            timestamp: "2026-04-18T09:00:00.000Z",
            metrics: {},
            summary: {
              overall_health: 0.7,
              data_points: 1,
              positive_signals: [],
              assessment: "Stable",
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }

      if (url.includes("/v1/improvement/summary")) {
        return new Response(
          JSON.stringify({
            total_proposals: 0,
            pending: 0,
            validated: 0,
            deployed: 0,
            failed: 0,
            benchmark_results: 0,
            last_cycle: null,
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }

      return new Response("not found", { status: 404 });
    }),
  );
}

describe("subpage data", () => {
  beforeEach(() => {
    const overview = getFixtureOverviewSnapshot();
    getProjectsSnapshot.mockResolvedValue({
      projects: overview.projects,
    });
    getWorkforceSnapshot.mockResolvedValue(buildWorkforceSnapshot());
    loadExecutionReviews.mockResolvedValue([
      {
        id: "approval:task-live-review",
        family: "builder",
        source: "operator_approval",
        owner_kind: "task",
        owner_id: "task-live-review",
        related_run_id: "run-task-live-review",
        related_task_id: "task-live-review",
        requested_action: "approve",
        privilege_class: "admin",
        reason: "Approve the live review-backed runtime packet.",
        status: "pending",
        requested_at: 1_800_000_000,
        task_prompt: "Approve the live review-backed runtime packet.",
        task_agent_id: "coding-agent",
        task_priority: "high",
        task_status: "pending_approval",
        deep_link: "/review?selection=approval%3Atask-live-review",
        metadata: {},
      },
    ]);
    loadExecutionResults.mockResolvedValue([
      {
        id: "builder-result:task-failed-review",
        family: "builder",
        source: "builder_front_door",
        owner_kind: "session",
        owner_id: "task-failed-review",
        related_run_id: "builder-run-task-failed-review",
        status: "failed",
        outcome: "failed",
        summary: "Queue inspection failed and needs operator review.",
        artifact_count: 0,
        artifacts: [],
        files_changed: [],
        validation: [],
        remaining_risks: ["Media queue state unresolved"],
        resumable_handle: null,
        recovery_gate: "resume_available",
        verification_status: "failed",
        updated_at: "2026-04-18T08:35:00.000Z",
        deep_link: "/builder?session=task-failed-review",
        metadata: {},
      },
      {
        id: "builder-result:task-completed-review",
        family: "builder",
        source: "builder_front_door",
        owner_kind: "session",
        owner_id: "task-completed-review",
        related_run_id: "builder-run-task-completed-review",
        status: "completed",
        outcome: "succeeded",
        summary: "Renderer diff finished and is ready for review.",
        artifact_count: 1,
        artifacts: [],
        files_changed: ["src/renderers/diff.ts"],
        validation: [],
        remaining_risks: [],
        resumable_handle: "codex-session-456",
        recovery_gate: null,
        verification_status: "passed",
        updated_at: "2026-04-18T08:34:00.000Z",
        deep_link: "/builder?session=task-completed-review",
        metadata: {},
      },
    ]);
    mockAgentFetch();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("counts only shared pending reviews and result-backed review items in history", async () => {
    const snapshot = await getHistorySnapshot();

    expect(snapshot.summary.reviewCount).toBe(3);
    expect("reviewTaskId" in (snapshot.activity[0] as Record<string, unknown>)).toBe(false);
    expect(snapshot.activity[0]?.reviewId).toBe("approval:task-live-review");
    expect(snapshot.activity[0]?.resultId).toBeNull();
    expect(snapshot.activity[1]?.reviewId).toBeNull();
    expect(snapshot.activity[1]?.resultId).toBeNull();
    expect(snapshot.activity[2]?.reviewId).toBeNull();
    expect(snapshot.activity[2]?.resultId).toBe("builder-result:task-failed-review");
    expect(snapshot.activity[3]?.reviewId).toBeNull();
    expect(snapshot.activity[3]?.resultId).toBeNull();
  });

  it("does not carry review-feed objects in the intelligence snapshot once review is kernel-native", async () => {
    const snapshot = await getIntelligenceSnapshot();

    expect("reviewItems" in snapshot).toBe(false);
    expect("reviewTasks" in snapshot).toBe(false);
    expect(snapshot.report?.timestamp).toBe("2026-04-18T09:00:00.000Z");
    expect(snapshot.learning?.summary.assessment).toBe("Stable");
  });

  it("builds a dedicated review snapshot from shared execution reviews and results", async () => {
    const snapshot = await getReviewSnapshot();

    expect(snapshot.reviewItems.map((item) => item.id)).toEqual([
      "approval:task-live-review",
      "builder-result:task-failed-review",
      "builder-result:task-completed-review",
    ]);
    expect(snapshot.reviewTasks.map((task) => task.id)).toEqual([
      "task-live-review",
      "task-failed-review",
      "task-completed-review",
    ]);
    expect(snapshot.reviewItems.find((item) => item.id === "builder-result:task-completed-review")).toMatchObject({
      kind: "result",
      taskId: "task-completed-review",
      resultSummary: "Renderer diff finished and is ready for review.",
      resultOutcome: "succeeded",
    });
  });
});
