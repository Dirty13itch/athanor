import { NextResponse } from "next/server";
import { config, joinUrl } from "@/lib/config";
import {
  FIXTURE_BASE_TIME,
  getFixtureAgentActivity,
  getFixtureAgentOutputs,
  getFixtureAgentPatterns,
  getFixtureAgentTasks,
  isDashboardFixtureMode,
} from "@/lib/dashboard-fixtures";

function parseFixtureBody(body: BodyInit | null | undefined) {
  if (typeof body !== "string") {
    return null;
  }

  try {
    return JSON.parse(body) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function buildFixtureAgentResponse(path: string, init: RequestInit | undefined) {
  const method = (init?.method ?? "GET").toUpperCase();
  const payload = parseFixtureBody(init?.body);
  const timestamp = FIXTURE_BASE_TIME;
  const requestUrl = new URL(`http://fixture${path}`);
  const limitParam = Number.parseInt(requestUrl.searchParams.get("limit") ?? "", 10);
  const limit = Number.isNaN(limitParam) ? null : limitParam;
  const agent = requestUrl.searchParams.get("agent");
  const basePath = path.split("?")[0];

  if (method === "GET" && basePath === "/v1/tasks") {
    const tasks = getFixtureAgentTasks({ agent, limit });
    return {
      tasks,
      count: tasks.length,
    };
  }

  if (method === "GET" && basePath === "/v1/activity") {
    const activity = getFixtureAgentActivity({ agent, limit });
    return {
      activity,
      count: activity.length,
    };
  }

  if (method === "GET" && basePath === "/v1/outputs") {
    const outputs = getFixtureAgentOutputs();
    return {
      outputs,
      count: outputs.length,
    };
  }

  if (method === "GET" && basePath === "/v1/patterns") {
    return getFixtureAgentPatterns({ agent });
  }

  if (method === "GET" && basePath === "/v1/subscriptions/providers") {
    return {
      providers: [
        { id: "anthropic_claude", name: "Anthropic Claude", default_task_class: "repo_wide_audit" },
        { id: "openai_codex", name: "OpenAI Codex", default_task_class: "async_backlog_execution" },
        { id: "google_gemini", name: "Google Gemini", default_task_class: "repo_wide_audit" },
        { id: "moonshot_kimi", name: "Moonshot Kimi", default_task_class: "search_heavy_planning" },
        { id: "zai_glm_coding", name: "Z.ai GLM", default_task_class: "cheap_bulk_transform" },
      ],
      count: 5,
      policy_source: "fixture-policy",
    };
  }

  if (method === "GET" && basePath === "/v1/subscriptions/policy") {
    return {
      version: "fixture-policy-v1",
      updated: timestamp,
      policy_source: "fixture-policy",
      providers: ["anthropic_claude", "openai_codex", "google_gemini", "moonshot_kimi", "zai_glm_coding"],
      task_classes: {
        async_backlog_execution: { primary: "openai_codex" },
        repo_wide_audit: { primary: "google_gemini" },
        search_heavy_planning: { primary: "moonshot_kimi" },
        multi_file_implementation: { primary: "anthropic_claude" },
        cheap_bulk_transform: { primary: "zai_glm_coding" },
      },
      agents: {
        "coding-agent": { default_task_class: "multi_file_implementation" },
        "research-agent": { default_task_class: "search_heavy_planning" },
      },
    };
  }

  if (method === "GET" && basePath === "/v1/subscriptions/leases") {
    return {
      leases: [
        {
          id: "lease-fixture-coding",
          requester: "coding-agent",
          provider: "anthropic_claude",
          task_class: "multi_file_implementation",
          expires_at: "2026-03-11T18:00:00Z",
        },
        {
          id: "lease-fixture-research",
          requester: "research-agent",
          provider: "google_gemini",
          task_class: "repo_wide_audit",
          expires_at: "2026-03-11T19:00:00Z",
        },
      ],
      count: 2,
    };
  }

  if (method === "POST" && basePath === "/v1/subscriptions/leases") {
    return {
      lease: {
        id: "lease-fixture-new",
        requester: typeof payload?.requester === "string" ? payload.requester : "coding-agent",
        provider: "anthropic_claude",
        task_class: typeof payload?.task_class === "string" ? payload.task_class : "multi_file_implementation",
        expires_at: "2026-03-11T20:00:00Z",
      },
      status: "issued",
      fixture: true,
    };
  }

  if (method === "GET" && basePath === "/v1/subscriptions/quotas") {
    return {
      policy_source: "fixture-policy",
      providers: {
        anthropic_claude: { status: "available", remaining: 18, limit: 25 },
        openai_codex: { status: "available", remaining: 9, limit: 12 },
        google_gemini: { status: "available", remaining: 23, limit: 30 },
        moonshot_kimi: { status: "available", remaining: 11, limit: 15 },
        zai_glm_coding: { status: "available", remaining: 120, limit: 160 },
      },
      recent_events: [
        { provider: "openai_codex", action: "lease_issued", timestamp },
        { provider: "google_gemini", action: "quota_refresh", timestamp },
      ],
    };
  }

  if (method === "GET" && basePath === "/v1/skills") {
    return {
      skills: [
        {
          skill_id: "repo-audit",
          name: "Repo Audit",
          description: "Audit large repo state and summarize the next execution batch.",
          category: "analysis",
          trigger_conditions: ["large repository changes", "needs architectural overview"],
          steps: ["scan state", "compare drift", "rank changes"],
          tags: ["repo", "audit"],
          execution_count: 16,
          success_rate: 0.94,
          avg_duration_ms: 820,
        },
        {
          skill_id: "deployment-verify",
          name: "Deployment Verify",
          description: "Check live endpoint posture against repo-backed deployment intent.",
          category: "operations",
          trigger_conditions: ["deployment drift", "service verification"],
          steps: ["probe", "diff", "report"],
          tags: ["deploy", "runtime"],
          execution_count: 11,
          success_rate: 0.91,
          avg_duration_ms: 1240,
        },
      ],
      count: 2,
    };
  }

  if (method === "GET" && basePath === "/v1/skills/top") {
    return {
      skills: [
        {
          skill_id: "repo-audit",
          name: "Repo Audit",
          category: "analysis",
          success_rate: 0.94,
          execution_count: 16,
        },
        {
          skill_id: "deployment-verify",
          name: "Deployment Verify",
          category: "operations",
          success_rate: 0.91,
          execution_count: 11,
        },
      ],
    };
  }

  if (method === "GET" && basePath === "/v1/skills/stats") {
    return {
      total: 12,
      executed: 47,
      categories: 5,
      avg_success_rate: 0.89,
      total_executions: 47,
    };
  }

  if (method === "GET" && /\/v1\/skills\/[^/]+$/.test(basePath)) {
    const skillId = basePath.split("/").at(-1);
    return {
      skill_id: skillId,
      name: skillId === "deployment-verify" ? "Deployment Verify" : "Repo Audit",
      description:
        skillId === "deployment-verify"
          ? "Check live endpoint posture against repo-backed deployment intent."
          : "Audit large repo state and summarize the next execution batch.",
      category: skillId === "deployment-verify" ? "operations" : "analysis",
      trigger_conditions: ["runtime drift", "large implementation batch"],
      steps: ["inspect inputs", "compare truth sources", "emit next actions"],
      tags: ["operator", "dashboard"],
      execution_count: skillId === "deployment-verify" ? 11 : 16,
      success_rate: skillId === "deployment-verify" ? 0.91 : 0.94,
      avg_duration_ms: skillId === "deployment-verify" ? 1240 : 820,
    };
  }

  if (method === "POST" && /\/v1\/skills\/[^/]+\/execution$/.test(basePath)) {
    return {
      status: "recorded",
      skill_id: basePath.split("/").at(-2),
      success: payload?.success ?? true,
      timestamp,
    };
  }

  if (method === "GET" && basePath === "/v1/research/jobs") {
    return [
      {
        job_id: "research-fixture-athanor",
        topic: "Athanor completion program",
        description: "Track the next autonomous execution batch and open risks.",
        status: "queued",
        schedule_hours: 0,
        updated_at: timestamp,
      },
      {
        job_id: "research-fixture-models",
        topic: "Subscription provider utilization",
        description: "Find the most productive coding allocation across providers.",
        status: "ready",
        schedule_hours: 24,
        updated_at: timestamp,
      },
    ];
  }

  if (method === "POST" && basePath === "/v1/research/jobs") {
    return {
      job_id: "research-fixture-new",
      topic: typeof payload?.topic === "string" ? payload.topic : "fixture research job",
      description: typeof payload?.description === "string" ? payload.description : "",
      status: "queued",
      schedule_hours: 0,
      updated_at: timestamp,
    };
  }

  if (method === "POST" && /\/v1\/research\/jobs\/[^/]+\/execute$/.test(basePath)) {
    return {
      status: "executed",
      job_id: basePath.split("/").at(-2),
      timestamp,
    };
  }

  if (method === "POST" && basePath === "/v1/consolidate") {
    return {
      status: "completed",
      timestamp,
      purged: {
        activity: 3,
        conversations: 1,
        implicit_feedback: 8,
        events: 4,
      },
    };
  }

  if (method === "GET" && basePath === "/v1/consolidate/stats") {
    return {
      activity: { count: 124, retention_days: 30 },
      conversations: { count: 48, retention_days: 14 },
      implicit_feedback: { count: 211, retention_days: 30 },
      events: { count: 93, retention_days: 21 },
    };
  }

  if (method === "GET" && basePath === "/v1/alerts") {
    return {
      alerts: [
        {
          name: "monitoring drift",
          severity: "warning",
          description: "Prometheus targets still need repo-side reconciliation on VAULT.",
        },
        {
          name: "subscription broker observed",
          severity: "info",
          description: "Premium-provider routing is available through the agent server.",
        },
      ],
      count: 2,
      history: [],
    };
  }

  if (method === "GET" && basePath === "/v1/notification-budget") {
    return {
      budgets: {
        "coding-agent": { allowed: true, used: 1, limit: 5, remaining: 4 },
        "research-agent": { allowed: true, used: 2, limit: 5, remaining: 3 },
        "general-assistant": { allowed: true, used: 1, limit: 6, remaining: 5 },
      },
    };
  }

  if (method === "GET" && basePath === "/v1/scheduling/status") {
    return {
      load: { current_ratio: 0.42 },
      thresholds: { warning: 0.7, critical: 0.9 },
      agent_classes: {
        coding: { max_concurrency: 2 },
        research: { max_concurrency: 2 },
        background: { max_concurrency: 1 },
      },
    };
  }

  if (method === "POST" && basePath === "/v1/context/preview") {
    const agent = typeof payload?.agent === "string" ? payload.agent : "general-assistant";
    const message = typeof payload?.message === "string" ? payload.message : "";
    return {
      agent,
      message,
      context: `Fixture context for ${agent}: repo drift summary, current workplan, and recent alerts.`,
      context_chars: 92,
      context_tokens_est: 23,
      duration_ms: 18,
    };
  }

  if (method === "POST" && basePath === "/v1/routing/classify") {
    return {
      tier: "premium",
      task_type: "repo_wide_audit",
      model: "google_gemini",
      max_tokens: 8192,
      temperature: 0.2,
      use_agent: true,
      confidence: 0.91,
      reason: "Large-context repo analysis routes to Gemini in fixture policy.",
      classification_ms: 9,
    };
  }

  if (method === "POST" && path === "/v1/patterns/run") {
    return { ok: true, fixture: true, queued: true, runId: "fixture-pattern-run", timestamp };
  }

  if (method === "POST" && path === "/v1/improvement/benchmarks/run") {
    return { ok: true, fixture: true, queued: true, runId: "fixture-benchmark-run", timestamp };
  }

  if (method === "POST" && path === "/v1/preferences") {
    return {
      ok: true,
      fixture: true,
      saved: true,
      timestamp,
      preference: {
        agentId: typeof payload?.agent === "string" ? payload.agent : "global",
        signalType: typeof payload?.signal_type === "string" ? payload.signal_type : "remember_this",
        content: typeof payload?.content === "string" ? payload.content : "",
        category: typeof payload?.category === "string" ? payload.category : null,
      },
    };
  }

  if (method === "POST" && /\/v1\/tasks\/[^/]+\/approve$/.test(path)) {
    return { ok: true, fixture: true, approved: true, taskId: path.split("/").at(-2), timestamp };
  }

  if (method === "POST" && /\/v1\/tasks\/[^/]+\/cancel$/.test(path)) {
    return { ok: true, fixture: true, canceled: true, taskId: path.split("/").at(-2), timestamp };
  }

  if (method === "POST" && /\/v1\/workspace\/[^/]+\/endorse$/.test(path)) {
    return { ok: true, fixture: true, endorsed: true, itemId: path.split("/").at(-2), timestamp };
  }

  if (method === "POST" && /\/v1\/notifications\/[^/]+\/resolve$/.test(path)) {
    return { ok: true, fixture: true, resolved: true, notificationId: path.split("/").at(-2), timestamp };
  }

  if (method === "POST" && /\/v1\/conventions\/[^/]+\/(confirm|reject)$/.test(path)) {
    return {
      ok: true,
      fixture: true,
      action: path.endsWith("/confirm") ? "confirm" : "reject",
      conventionId: path.split("/").at(-2),
      timestamp,
    };
  }

  if (["POST", "PATCH", "PUT", "DELETE"].includes(method)) {
    return { ok: true, fixture: true, path, method, timestamp };
  }

  return null;
}

export async function proxyAgentJson(
  path: string,
  init: RequestInit | undefined,
  errorMessage: string,
  timeoutMs = 10_000
) {
  if (isDashboardFixtureMode()) {
    const fixtureResponse = buildFixtureAgentResponse(path, init);
    if (fixtureResponse) {
      return NextResponse.json(fixtureResponse);
    }
  }

  try {
    const response = await fetch(joinUrl(config.agentServer.url, path), {
      ...init,
      signal: init?.signal ?? AbortSignal.timeout(timeoutMs),
    });

    if (!response.ok) {
      return NextResponse.json({ error: `Upstream returned ${response.status}` }, { status: response.status });
    }

    const text = await response.text();
    return NextResponse.json(text ? JSON.parse(text) : { ok: true });
  } catch {
    return NextResponse.json({ error: errorMessage }, { status: 502 });
  }
}
