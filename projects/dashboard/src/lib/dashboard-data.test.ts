import { afterEach, describe, expect, it, vi } from "vitest";

import { __testing } from "./dashboard-data";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("dashboard service health normalization", () => {
  it("summarizes scheduled queue pressure from queue-backed vs direct jobs", () => {
    const summary = __testing.summarizeScheduledJobPressure([
      {
        id: "agent-schedule:coding-agent",
        last_execution_mode: "materialized_to_backlog",
        last_execution_plane: "queue",
        last_admission_classification: "queue",
        last_backlog_id: "backlog-coding-1",
      },
      {
        id: "research:daily-audit",
        last_execution_mode: "materialized_to_backlog",
        last_execution_plane: "queue",
        last_admission_classification: "queue",
        last_backlog_id: null,
      },
      {
        id: "daily-digest",
        last_execution_mode: "executed_directly",
        last_execution_plane: "direct_control",
        last_admission_classification: "direct_control",
        last_backlog_id: null,
      },
    ]);

    expect(summary).toEqual({
      totalJobs: 3,
      queueBackedJobs: 2,
      directJobs: 1,
      proposalOnlyJobs: 0,
      blockedJobs: 0,
      needsSyncJobs: 1,
    });
  });

  it("counts approval and failure posture from explicit review/result evidence", () => {
    const tasks = [
      {
        id: "task-approval-real",
        agentId: "coding-agent",
        status: "pending_approval" as const,
        reviewId: "approval:task-approval-real",
        resultId: null,
      },
      {
        id: "task-approval-stale",
        agentId: "coding-agent",
        status: "pending_approval" as const,
        reviewId: null,
        resultId: null,
      },
      {
        id: "task-failed-real",
        agentId: "research-agent",
        status: "failed" as const,
        reviewId: null,
        resultId: "builder-result:task-failed-real",
      },
      {
        id: "task-failed-stale",
        agentId: "research-agent",
        status: "failed" as const,
        reviewId: null,
        resultId: null,
      },
      {
        id: "task-pending",
        agentId: "coding-agent",
        status: "pending" as const,
        reviewId: null,
        resultId: null,
      },
    ];

    expect(__testing.hasPendingApprovalEvidence(tasks[0]!)).toBe(true);
    expect(__testing.hasPendingApprovalEvidence(tasks[1]!)).toBe(false);
    expect(__testing.hasFailedResultEvidence(tasks[2]!)).toBe(true);
    expect(__testing.hasFailedResultEvidence(tasks[3]!)).toBe(false);
    expect(__testing.countPendingApprovalEvidence(tasks)).toBe(1);
    expect(__testing.countFailedResultEvidence(tasks)).toBe(1);
  });

  it("uses explicit review/result evidence in project and agent posture rollups", () => {
    const tasks = [
      {
        id: "task-approval-real",
        agentId: "coding-agent",
        prompt: "Approval-backed task",
        priority: "high" as const,
        status: "pending_approval" as const,
        createdAt: "2026-03-09T15:00:00.000Z",
        startedAt: null,
        completedAt: null,
        durationMs: null,
        requiresApproval: true,
        reviewId: "approval:task-approval-real",
        resultId: null,
        source: "work_planner",
        projectId: "athanor",
        planId: null,
        rationale: null,
        parentTaskId: null,
        result: null,
        error: null,
        stepCount: 0,
      },
      {
        id: "task-approval-stale",
        agentId: "coding-agent",
        prompt: "Status-only approval task",
        priority: "normal" as const,
        status: "pending_approval" as const,
        createdAt: "2026-03-09T15:01:00.000Z",
        startedAt: null,
        completedAt: null,
        durationMs: null,
        requiresApproval: true,
        reviewId: null,
        resultId: null,
        source: "work_planner",
        projectId: "athanor",
        planId: null,
        rationale: null,
        parentTaskId: null,
        result: null,
        error: null,
        stepCount: 0,
      },
      {
        id: "task-failed-real",
        agentId: "research-agent",
        prompt: "Result-backed failure",
        priority: "normal" as const,
        status: "failed" as const,
        createdAt: "2026-03-09T15:02:00.000Z",
        startedAt: null,
        completedAt: "2026-03-09T15:03:00.000Z",
        durationMs: 60_000,
        requiresApproval: false,
        reviewId: null,
        resultId: "builder-result:task-failed-real",
        source: "work_planner",
        projectId: "athanor",
        planId: null,
        rationale: null,
        parentTaskId: null,
        result: null,
        error: "failed",
        stepCount: 1,
      },
      {
        id: "task-failed-stale",
        agentId: "research-agent",
        prompt: "Status-only failure",
        priority: "normal" as const,
        status: "failed" as const,
        createdAt: "2026-03-09T15:04:00.000Z",
        startedAt: null,
        completedAt: "2026-03-09T15:05:00.000Z",
        durationMs: 60_000,
        requiresApproval: false,
        reviewId: null,
        resultId: null,
        source: "work_planner",
        projectId: "athanor",
        planId: null,
        rationale: null,
        parentTaskId: null,
        result: null,
        error: "failed",
        stepCount: 1,
      },
      {
        id: "task-pending",
        agentId: "coding-agent",
        prompt: "Queued task",
        priority: "normal" as const,
        status: "pending" as const,
        createdAt: "2026-03-09T15:06:00.000Z",
        startedAt: null,
        completedAt: null,
        durationMs: null,
        requiresApproval: false,
        reviewId: null,
        resultId: null,
        source: "work_planner",
        projectId: "athanor",
        planId: null,
        rationale: null,
        parentTaskId: null,
        result: null,
        error: null,
        stepCount: 0,
      },
    ];

    const projects = __testing.buildProjectPostures(
      [
        {
          id: "athanor",
          name: "Athanor",
          description: "Core control plane",
          headline: "Athanor",
          status: "active",
          kind: "core" as const,
          firstClass: true,
          lens: "operator",
          primaryRoute: "/",
          externalUrl: null,
          agents: ["coding-agent", "research-agent"],
          needsCount: 1,
          constraints: [],
          operatorChain: ["builder"],
        },
      ],
      tasks,
      null,
    );
    const agentRollup = __testing.buildWorkforceAgents(
      [
        {
          id: "coding-agent",
          name: "Coding Agent",
          description: "Implements code changes",
          icon: "code",
          tools: [],
          status: "ready" as const,
          type: "proactive",
        },
        {
          id: "research-agent",
          name: "Research Agent",
          description: "Runs analysis",
          icon: "search",
          tools: [],
          status: "ready" as const,
          type: "reactive",
        },
      ],
      tasks,
      {},
    );

    expect(projects[0]?.pendingApprovals).toBe(1);
    expect(projects[0]?.failedTasks).toBe(1);
    expect(agentRollup.find((agent) => agent.id === "coding-agent")?.pendingTasks).toBe(2);
    expect(agentRollup.find((agent) => agent.id === "research-agent")?.pendingTasks).toBe(0);
  });

  it("maps explicit execution results onto task ids", () => {
    const resultIds = __testing.buildExecutionResultIdMap([
      { id: "builder-result:task-1", owner_id: "task-1", status: "failed" },
      { id: "builder-result:task-2", owner_id: "task-2", status: "completed" },
      { id: "builder-result:task-3", owner_id: "task-3", status: "running" },
      { id: "builder-result:task-4", owner_id: "", status: "failed" },
    ]);

    expect(resultIds.get("task-1")).toBe("builder-result:task-1");
    expect(resultIds.get("task-2")).toBe("builder-result:task-2");
    expect(resultIds.has("task-3")).toBe(false);
    expect(resultIds.has("")).toBe(false);
  });

  it("treats model catalog responses as healthy service probes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ data: [{ id: "dolphin3-r1-24b" }] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "foundry-coder",
      name: "Foundry Coder",
      nodeId: "node1",
      node: "Foundry",
      category: "inference",
      description: "Autonomous dolphin coding runtime on the 4090 lane.",
      url: "http://192.168.1.244:8100/v1/models",
    });

    expect(snapshot.healthy).toBe(true);
    expect(snapshot.state).toBe("healthy");
    expect(snapshot.lastError).toBeNull();
  });

  it("treats configured pass-through probe endpoints as healthy on 200 responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("Prometheus is Healthy.", {
          status: 200,
          headers: { "content-type": "text/plain" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "prometheus",
      name: "Prometheus",
      nodeId: "vault",
      node: "VAULT",
      category: "observability",
      description: "Metrics and scrape surface.",
      url: "http://192.168.1.203:9090/-/healthy",
    });

    expect(snapshot.healthy).toBe(true);
    expect(snapshot.state).toBe("healthy");
    expect(snapshot.lastError).toBeNull();
  });

  it("treats ComfyUI as healthy when Workshop answers on its own runtime contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ system: { comfyui_version: "0.18.1" } }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "comfyui",
      name: "ComfyUI",
      nodeId: "node2",
      node: "Workshop",
      category: "experience",
      description: "Creative workflow runtime.",
      url: "http://192.168.1.225:8188/system_stats",
    });

    expect(snapshot.healthy).toBe(true);
    expect(snapshot.state).toBe("healthy");
    expect(snapshot.lastError).toBeNull();
  });

  it("treats Workshop Open WebUI as healthy when the UI responds without the shared contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<html><body>Open WebUI</body></html>", {
          status: 200,
          headers: { "content-type": "text/html" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "workshop-open-webui",
      name: "Workshop Open WebUI",
      nodeId: "node2",
      node: "Workshop",
      category: "experience",
      description: "Direct local chat surface for raw model access.",
      url: "http://192.168.1.225:3000",
    });

    expect(snapshot.healthy).toBe(true);
    expect(snapshot.state).toBe("healthy");
    expect(snapshot.lastError).toBeNull();
  });

  it("passes configured auth headers to service probes", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("ok", {
        status: 200,
        headers: { "content-type": "text/plain" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await __testing.checkService({
      id: "home-assistant",
      name: "Home Assistant",
      nodeId: "vault",
      node: "VAULT",
      category: "home",
      description: "Smart-home control plane and automation state.",
      url: "http://192.168.1.203:8123/api/",
      headers: { Authorization: "Bearer test-token" },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://192.168.1.203:8123/api/",
      expect.objectContaining({
        headers: { Authorization: "Bearer test-token" },
      })
    );
  });

  it("treats auth-guarded pass-through services as warning instead of contract drift", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("401: Unauthorized", {
          status: 401,
          headers: { "content-type": "text/plain" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "home-assistant",
      name: "Home Assistant",
      nodeId: "vault",
      node: "VAULT",
      category: "home",
      description: "Smart-home control plane and automation state.",
      url: "http://192.168.1.203:8123/api/",
    });

    expect(snapshot.healthy).toBe(true);
    expect(snapshot.state).toBe("warning");
    expect(snapshot.lastError).toBe("Service is reachable but requires auth for the health probe.");
  });

  it("preserves fetch failures as degraded probe detail", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED 192.168.1.189:8001")));

    const snapshot = await __testing.checkService({
      id: "dev-embedding",
      name: "DEV Embedding",
      nodeId: "dev",
      node: "DEV",
      category: "knowledge",
      description: "Embedding runtime for retrieval, indexing, and semantic search.",
      url: "http://192.168.1.189:8001/v1/models",
    });

    expect(snapshot.healthy).toBe(false);
    expect(snapshot.state).toBe("degraded");
    expect(snapshot.lastError).toContain("ECONNREFUSED");
  });

  it("normalizes aborts into explicit timeout detail", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("This operation was aborted", "AbortError")));

    const snapshot = await __testing.checkService({
      id: "comfyui",
      name: "ComfyUI",
      nodeId: "node2",
      node: "Workshop",
      category: "experience",
      description: "Creative workflow runtime.",
      url: "http://192.168.1.225:8188/system_stats",
      probeTimeoutMs: 7000,
    });

    expect(snapshot.healthy).toBe(false);
    expect(snapshot.state).toBe("degraded");
    expect(snapshot.lastError).toBe("Probe timed out after 7000ms");
  });

  it("uses service-specific probe timeouts when provided", async () => {
    const setTimeoutSpy = vi.spyOn(globalThis, "setTimeout");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ data: [{ id: "general-assistant" }] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "agent-server",
      name: "Agent Server",
      nodeId: "node1",
      node: "Foundry",
      category: "platform",
      description: "FastAPI runtime for the Athanor workforce and task APIs.",
      url: "http://192.168.1.244:9000/health",
      probeTimeoutMs: 10000,
    });

    expect(snapshot.healthy).toBe(true);
    expect(setTimeoutSpy.mock.calls[0]?.[1]).toBe(10000);
  });
});
