import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/executive-kernel", () => ({
  loadExecutionReviewFeed: vi.fn(async () => ({
    available: true,
    degraded: false,
    source: "shared_execution_kernel",
    detail: null,
    reviews: [],
    count: 0,
  })),
}));

import { GET } from "./route";
import { loadExecutionReviewFeed } from "@/lib/executive-kernel";

describe("operator approvals api route", () => {
  beforeEach(() => {
    vi.mocked(loadExecutionReviewFeed).mockReset();
    vi.mocked(loadExecutionReviewFeed).mockResolvedValue({
      available: true,
      degraded: false,
      source: "shared_execution_kernel",
      detail: null,
      reviews: [],
      count: 0,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("projects the shared execution review feed into approval-shaped compatibility records", async () => {
    vi.mocked(loadExecutionReviewFeed).mockResolvedValueOnce({
      available: true,
      degraded: false,
      source: "shared_execution_kernel",
      detail: null,
      reviews: [
        {
          id: "approval:task-home-1",
          family: "home_ops",
          source: "operator_approval",
          owner_kind: "task",
          owner_id: "task-home-1",
          related_run_id: "approval:task-home-1",
          related_task_id: "task-home-1",
          requested_action: "approve",
          privilege_class: "admin",
          reason: "Approve the home automation adjustment.",
          status: "pending",
          requested_at: 1710000000,
          task_prompt: "Adjust the evening lighting automation after the recent occupancy drift report.",
          task_agent_id: "home-agent",
          task_priority: "high",
          task_status: "pending_approval",
          deep_link: "/review?selection=task-home-1",
          metadata: {},
        },
      ],
      count: 1,
    });

    const response = await GET(new NextRequest("http://localhost/api/operator/approvals?status=pending"));

    expect(response.status).toBe(200);
    expect(loadExecutionReviewFeed).toHaveBeenCalledWith({
      status: "pending",
      family: null,
      limit: 500,
    });
    await expect(response.json()).resolves.toMatchObject({
      available: true,
      degraded: false,
      approvals: [
        expect.objectContaining({
          id: "approval:task-home-1",
          related_task_id: "task-home-1",
          task_agent_id: "home-agent",
          task_status: "pending_approval",
          status: "pending",
        }),
      ],
      count: 1,
    });
  });

  it("preserves degraded status when the shared execution review feed is incomplete", async () => {
    vi.mocked(loadExecutionReviewFeed).mockResolvedValueOnce({
      available: false,
      degraded: true,
      source: "shared_execution_kernel",
      detail: "Operator approval feed unavailable from agent server.",
      reviews: [],
      count: 0,
    });

    const response = await GET(new NextRequest("http://localhost/api/operator/approvals?status=pending"));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      available: false,
      degraded: true,
      detail: "Operator approval feed unavailable from agent server.",
      approvals: [],
      count: 0,
    });
  });

  it("keeps builder and bootstrap reviews visible through the compatibility projection", async () => {
    vi.mocked(loadExecutionReviewFeed).mockResolvedValueOnce({
      available: true,
      degraded: false,
      source: "shared_execution_kernel",
      detail: null,
      reviews: [
        {
          id: "builder-approval-1",
          family: "builder",
          source: "builder_front_door",
          owner_kind: "session",
          owner_id: "builder-1",
          related_run_id: "builder-run-builder-1",
          related_task_id: "builder-1",
          requested_action: "approve",
          privilege_class: "admin",
          reason: "Approve the builder session.",
          status: "pending",
          requested_at: 1710000000,
          task_prompt: "Implement the bounded Codex route.",
          task_agent_id: "codex",
          task_priority: "normal",
          task_status: "waiting_approval",
          deep_link: "/builder?session=builder-1",
          metadata: { builder_session_id: "builder-1" },
        },
        {
          id: "bootstrap-approval:launch-readiness-bootstrap:persist-04-activation-cutover:db_schema_change",
          family: "bootstrap_takeover",
          source: "bootstrap_program",
          owner_kind: "program",
          owner_id: "launch-readiness-bootstrap",
          related_run_id: "bootstrap-program:launch-readiness-bootstrap",
          related_task_id: "persist-04-activation-cutover",
          requested_action: "approve",
          privilege_class: "admin",
          reason: "Authorize the durable persistence schema and runtime cutover maintenance window.",
          status: "pending",
          requested_at: 1710000010,
          task_prompt: "Drive the external builder lane to takeover readiness.",
          task_agent_id: "durable_persistence_activation",
          task_priority: "high",
          task_status: "waiting_approval",
          deep_link: "/bootstrap?program=launch-readiness-bootstrap&slice=persist-04-activation-cutover",
          metadata: {
            bootstrap_program_id: "launch-readiness-bootstrap",
            bootstrap_slice_id: "persist-04-activation-cutover",
            packet_id: "db_schema_change",
          },
        },
      ],
      count: 2,
    });

    const response = await GET(new NextRequest("http://localhost/api/operator/approvals?status=pending"));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      approvals: expect.arrayContaining([
        expect.objectContaining({
          id: "bootstrap-approval:launch-readiness-bootstrap:persist-04-activation-cutover:db_schema_change",
          related_task_id: "persist-04-activation-cutover",
          task_agent_id: "durable_persistence_activation",
          status: "pending",
        }),
        expect.objectContaining({
          id: "builder-approval-1",
          related_task_id: "builder-1",
          task_agent_id: "codex",
          status: "pending",
        }),
      ]),
      count: 2,
    });
  });
});
