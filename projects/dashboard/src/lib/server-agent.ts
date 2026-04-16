import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { agentServerHeaders, config, joinUrl } from "@/lib/config";
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

function buildFixtureActivityStats(agentId: string | null) {
  const byAgent: Record<string, { tasks_completed: number; tasks_failed: number; avg_duration_ms: number }> = {
    "general-assistant": { tasks_completed: 28, tasks_failed: 1, avg_duration_ms: 4200 },
    "coding-agent": { tasks_completed: 14, tasks_failed: 2, avg_duration_ms: 6800 },
    "research-agent": { tasks_completed: 11, tasks_failed: 1, avg_duration_ms: 9100 },
  };

  return byAgent[agentId ?? ""] ?? {
    tasks_completed: 9,
    tasks_failed: 1,
    avg_duration_ms: 5400,
  };
}

function buildFixtureImprovementSummary(timestamp: string) {
  return {
    last_cycle: timestamp,
    proposals_generated: 3,
    proposals_deployed: 2,
    cycle_duration_ms: 18420,
    benchmark_pass_rate: 0.86,
  };
}

function buildFixtureImprovementProposals() {
  return [
    {
      id: "proposal-routing-tier",
      agent_name: "Coding Agent",
      variant_description: "Tighten routing fallback policy for repo-wide audits.",
      status: "deployed",
      improvement_pct: 12.4,
    },
    {
      id: "proposal-review-packet",
      agent_name: "Research Agent",
      variant_description: "Bias toward packet-backed review summaries for long-running reconciliation work.",
      status: "validated",
      improvement_pct: 7.1,
    },
    {
      id: "proposal-operator-brief",
      agent_name: "General Assistant",
      variant_description: "Shorten command-center daily brief framing while keeping residue counts explicit.",
      status: "pending",
      improvement_pct: null,
    },
  ];
}

function buildFixtureBenchmarkHistory(timestamp: string) {
  const base = new Date(timestamp).getTime();
  return [
    { date: new Date(base - 4 * 86_400_000).toISOString(), pass_count: 16, total_count: 20, pass_rate: 0.8 },
    { date: new Date(base - 3 * 86_400_000).toISOString(), pass_count: 17, total_count: 20, pass_rate: 0.85 },
    { date: new Date(base - 2 * 86_400_000).toISOString(), pass_count: 18, total_count: 20, pass_rate: 0.9 },
    { date: new Date(base - 1 * 86_400_000).toISOString(), pass_count: 17, total_count: 20, pass_rate: 0.85 },
    { date: new Date(base).toISOString(), pass_count: 19, total_count: 22, pass_rate: 19 / 22 },
  ];
}

const FIXTURE_GOVERNOR_LANES = [
  {
    id: "task_worker",
    label: "Task worker",
    description: "Durable task execution loop for queued background work.",
  },
  {
    id: "scheduler",
    label: "Scheduler",
    description: "Recurring automation and proactive agent scheduling.",
  },
  {
    id: "research_jobs",
    label: "Research jobs",
    description: "Autonomous research-job triggering inside the scheduler.",
  },
  {
    id: "benchmark_cycle",
    label: "Benchmark cycle",
    description: "Model-proving and self-improvement benchmark cadence.",
  },
];

const FIXTURE_PRESENCE_PROFILES = {
  at_desk: {
    label: "At desk",
    automation_posture: "normal bounded autonomy",
    notification_posture: "full detail",
    approval_posture: "low friction",
  },
  away: {
    label: "Away",
    automation_posture: "conservative autonomous execution",
    notification_posture: "digest first",
    approval_posture: "medium friction",
  },
  asleep: {
    label: "Asleep",
    automation_posture: "protective defer-only posture",
    notification_posture: "quiet digest",
    approval_posture: "high friction",
  },
  phone_only: {
    label: "Phone only",
    automation_posture: "bounded mobile posture",
    notification_posture: "quiet digest",
    approval_posture: "summary approval only",
  },
} as const;

const FIXTURE_SESSION_COOKIE = "athanor_fixture_session";
const FIXTURE_GOVERNOR_STATE_COOKIE = "athanor_fixture_governor_state";

type FixtureGovernorState = {
  global_mode: string;
  degraded_mode: string;
  paused_lanes: string[];
  reason: string;
  updated_at: string | null;
  updated_by: string;
  operator_presence: keyof typeof FIXTURE_PRESENCE_PROFILES;
  presence_mode: "auto" | "manual";
  presence_reason: string;
  presence_updated_at: string | null;
  presence_updated_by: string;
  presence_signal_state: keyof typeof FIXTURE_PRESENCE_PROFILES | null;
  presence_signal_source: string;
  presence_signal_reason: string;
  presence_signal_updated_at: string | null;
  presence_signal_updated_by: string;
  release_tier: string;
  tier_reason: string;
  tier_updated_at: string | null;
  tier_updated_by: string;
};

const DEFAULT_FIXTURE_GOVERNOR_STATE: FixtureGovernorState = {
  global_mode: "active",
  degraded_mode: "normal",
  paused_lanes: [],
  reason: "",
  updated_at: null,
  updated_by: "fixture-operator",
  operator_presence: "at_desk",
  presence_mode: "auto",
  presence_reason: "",
  presence_updated_at: null,
  presence_updated_by: "fixture-operator",
  presence_signal_state: "at_desk",
  presence_signal_source: "dashboard_heartbeat",
  presence_signal_reason: "Fixture dashboard heartbeat is active.",
  presence_signal_updated_at: FIXTURE_BASE_TIME,
  presence_signal_updated_by: "dashboard-heartbeat",
  release_tier: "production",
  tier_reason: "",
  tier_updated_at: null,
  tier_updated_by: "fixture-operator",
};

const FIXTURE_GOVERNOR_STATES = new Map<string, FixtureGovernorState>();

type FixtureOperatorTestFlow = {
  id: string;
  title: string;
  description: string;
  status: string;
  last_outcome: string | null;
  last_run_at: string | null;
  last_duration_ms: number | null;
  checks_passed: number;
  checks_total: number;
  evidence: string[];
  notes: string[];
  details?: Record<string, unknown>;
};

type FixtureOperatorTestsState = {
  last_run_at: string | null;
  last_outcome: string;
  flows: FixtureOperatorTestFlow[];
};

const FIXTURE_OPERATOR_TEST_STATES = new Map<string, FixtureOperatorTestsState>();

type FixturePromotionRecord = {
  id: string;
  asset_class: string;
  role_id: string;
  role_label: string;
  plane: string;
  candidate: string;
  champion: string;
  current_tier: string;
  target_tier: string;
  status: string;
  reason: string;
  created_at: string;
  updated_at: string;
  updated_by: string;
  source: string;
  rollout_steps: string[];
  next_tier: string | null;
  completed_at: string | null;
  rollback_target: string | null;
  notes: string[];
};

type FixturePromotionState = {
  records: FixturePromotionRecord[];
  events: Array<Record<string, unknown>>;
};

const FIXTURE_PROMOTION_STATES = new Map<string, FixturePromotionState>();

type FixtureRetirementRecord = {
  id: string;
  asset_class: string;
  asset_id: string;
  label: string;
  current_stage: string;
  target_stage: string;
  status: string;
  reason: string;
  created_at: string;
  updated_at: string;
  updated_by: string;
  source: string;
  next_stage: string | null;
  completed_at: string | null;
  rollback_target: string | null;
  notes: string[];
};

type FixtureRetirementState = {
  records: FixtureRetirementRecord[];
  events: Array<Record<string, unknown>>;
};

const FIXTURE_RETIREMENT_STATES = new Map<string, FixtureRetirementState>();

async function getFixtureSessionId() {
  try {
    const cookieStore = await cookies();
    return cookieStore.get(FIXTURE_SESSION_COOKIE)?.value ?? "default";
  } catch {
    return "default";
  }
}

function parseFixtureGovernorStateCookie(
  value: string | undefined
): FixtureGovernorState | null {
  if (!value) {
    return null;
  }

  try {
    const parsed = JSON.parse(decodeURIComponent(value)) as Partial<FixtureGovernorState>;
    return {
      ...DEFAULT_FIXTURE_GOVERNOR_STATE,
      ...parsed,
      paused_lanes: Array.isArray(parsed.paused_lanes)
        ? parsed.paused_lanes.filter((lane): lane is string => typeof lane === "string")
        : [...DEFAULT_FIXTURE_GOVERNOR_STATE.paused_lanes],
      operator_presence:
        typeof parsed.operator_presence === "string" &&
        parsed.operator_presence in FIXTURE_PRESENCE_PROFILES
          ? (parsed.operator_presence as keyof typeof FIXTURE_PRESENCE_PROFILES)
          : DEFAULT_FIXTURE_GOVERNOR_STATE.operator_presence,
      presence_mode:
        parsed.presence_mode === "auto" || parsed.presence_mode === "manual"
          ? parsed.presence_mode
          : DEFAULT_FIXTURE_GOVERNOR_STATE.presence_mode,
      presence_signal_state:
        typeof parsed.presence_signal_state === "string" &&
        parsed.presence_signal_state in FIXTURE_PRESENCE_PROFILES
          ? (parsed.presence_signal_state as keyof typeof FIXTURE_PRESENCE_PROFILES)
          : DEFAULT_FIXTURE_GOVERNOR_STATE.presence_signal_state,
      release_tier:
        typeof parsed.release_tier === "string" &&
        ["offline_eval", "shadow", "sandbox", "canary", "production"].includes(
          parsed.release_tier
        )
          ? parsed.release_tier
          : DEFAULT_FIXTURE_GOVERNOR_STATE.release_tier,
    };
  } catch {
    return null;
  }
}

function serializeFixtureGovernorState(state: FixtureGovernorState) {
  return encodeURIComponent(JSON.stringify(state));
}

function createFixtureGovernorState(): FixtureGovernorState {
  return {
    ...DEFAULT_FIXTURE_GOVERNOR_STATE,
    paused_lanes: [...DEFAULT_FIXTURE_GOVERNOR_STATE.paused_lanes],
  };
}

async function getFixtureGovernorState() {
  const sessionId = await getFixtureSessionId();
  const existing = FIXTURE_GOVERNOR_STATES.get(sessionId);
  if (existing) {
    return existing;
  }

  try {
    const cookieStore = await cookies();
    const cookieState = parseFixtureGovernorStateCookie(
      cookieStore.get(FIXTURE_GOVERNOR_STATE_COOKIE)?.value
    );
    if (cookieState) {
      FIXTURE_GOVERNOR_STATES.set(sessionId, cookieState);
      return cookieState;
    }
  } catch {}
  const created = createFixtureGovernorState();
  FIXTURE_GOVERNOR_STATES.set(sessionId, created);
  return created;
}

function createFixturePromotionState(timestamp: string): FixturePromotionState {
  return {
    records: [
      {
        id: "promotion-frontier-gemini",
        asset_class: "models",
        role_id: "frontier_supervisor",
        role_label: "Frontier supervisor",
        plane: "frontier_cloud",
        candidate: "Gemini",
        champion: "Claude",
        current_tier: "shadow",
        target_tier: "canary",
        status: "active",
        reason: "Gemini is under governed promotion for large-context repo audit work.",
        created_at: "2026-03-12T06:00:00Z",
        updated_at: "2026-03-12T06:15:00Z",
        updated_by: "fixture-operator",
        source: "fixture_model_governance",
        rollout_steps: [
          "prepare candidate",
          "run offline eval and policy checks",
          "enable shadow mode",
          "promote to canary",
          "verify guardrail and operator outcomes",
          "promote to production or rollback",
          "record outcome in experiment ledger",
        ],
        next_tier: "canary",
        completed_at: null,
        rollback_target: null,
        notes: ["Previous champion remains available until canary succeeds."],
      },
    ],
    events: [
      {
        event: "promotion_staged",
        promotion_id: "promotion-frontier-gemini",
        role_id: "frontier_supervisor",
        candidate: "Gemini",
        target_tier: "canary",
        timestamp,
        actor: "fixture-operator",
      },
    ],
  };
}

async function getFixturePromotionState(timestamp: string) {
  const sessionId = await getFixtureSessionId();
  const existing = FIXTURE_PROMOTION_STATES.get(sessionId);
  if (existing) {
    return existing;
  }
  const created = createFixturePromotionState(timestamp);
  FIXTURE_PROMOTION_STATES.set(sessionId, created);
  return created;
}

function createFixtureRetirementState(): FixtureRetirementState {
  return {
    records: [],
    events: [],
  };
}

async function getFixtureRetirementState() {
  const sessionId = await getFixtureSessionId();
  const existing = FIXTURE_RETIREMENT_STATES.get(sessionId);
  if (existing) {
    return existing;
  }
  const created = createFixtureRetirementState();
  FIXTURE_RETIREMENT_STATES.set(sessionId, created);
  return created;
}

function createFixtureOperatorTestsState(timestamp: string): FixtureOperatorTestsState {
  return {
    last_run_at: null,
    last_outcome: "not_run",
    flows: [
      {
        id: "pause_resume",
        title: "Pause and resume automation",
        description: "Exercises live lane pause and resume controls through the governor while restoring prior state.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 4,
        evidence: ["test_governor.py", "tests/e2e/operator-controls.spec.ts"],
        notes: [],
      },
      {
        id: "presence_tier",
        title: "Presence and release-tier posture",
        description: "Verifies presence-aware and release-tier-aware governance decisions with safe restore of prior posture.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 4,
        evidence: ["test_governor.py", "tests/e2e/operator-controls.spec.ts"],
        notes: [],
      },
      {
        id: "scheduled_job_governance",
        title: "Scheduled job posture and deferral",
        description: "Checks that scheduled jobs expose governor-owned state, cadence, deep links, and execution posture.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 5,
        evidence: ["test_backbone.py"],
        notes: [],
      },
      {
        id: "sovereign_routing",
        title: "Sovereign routing verification",
        description: "Verifies refusal-sensitive work stays sovereign and cloud-safe work remains eligible for frontier supervision.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 5,
        evidence: ["test_operator_tests.py"],
        notes: [],
      },
      {
        id: "provider_fallback",
        title: "Provider fallback readiness",
        description: "Checks governed provider fallback posture, handoff availability, and recent lease evidence without bypassing the governor.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 4,
        evidence: ["test_operator_tests.py", "test_provider_execution.py"],
        notes: [],
      },
      {
        id: "stuck_queue_recovery",
        title: "Stuck queue recovery",
        description: "Exercises non-destructive queue recovery posture by pausing a governed lane, verifying scheduled-job state, and restoring forward progress cleanly.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 5,
        evidence: ["test_operator_tests.py", "test_governor.py", "test_backbone.py"],
        notes: [],
      },
      {
        id: "incident_review",
        title: "Incident review",
        description: "Verifies that alerts, operator stream events, and execution-run lineage can be reviewed together without SSH or log scraping.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 5,
        evidence: ["test_operator_tests.py", "test_backbone.py"],
        notes: [],
      },
      {
        id: "tool_permissions",
        title: "Tool-permission governance",
        description: "Verifies live tool-permission decisions across meta lanes, specialists, workers, and judges.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 6,
        evidence: ["test_operator_tests.py", "test_tool_permissions.py"],
        notes: [],
      },
      {
        id: "economic_governance",
        title: "Economic governance verification",
        description: "Checks reserve lanes, approval-required spend, and downgrade posture against live provider summaries.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 5,
        evidence: ["test_operator_tests.py", "subscription-routing-policy.yaml"],
        notes: [],
      },
      {
        id: "promotion_ladder",
        title: "Promotion ladder rehearsal",
        description: "Stages, advances, and rolls back a challenger through the governed release ladder without leaving production state mutated.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 6,
        evidence: ["test_operator_tests.py", "test_promotion_control.py"],
        notes: [],
      },
      {
        id: "retirement_policy",
        title: "Retirement policy rehearsal",
        description: "Stages, advances, and rolls back a governed retirement candidate so deprecation posture is backed by live evidence instead of registry text alone.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 6,
        evidence: ["test_operator_tests.py", "test_retirement_control.py"],
        notes: [],
      },
      {
        id: "data_lifecycle",
        title: "Data lifecycle verification",
        description: "Checks that operational history, sovereign content, and eval artifacts are backed by live runtime evidence.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 5,
        evidence: ["test_operator_tests.py", "data-lifecycle-registry.json"],
        notes: [],
      },
      {
        id: "restore_drill",
        title: "Restore drill and recovery flow",
        description: "Captures non-destructive live restore evidence for critical stores while preserving governed recovery ordering.",
        status: "configured",
        last_outcome: null,
        last_run_at: null,
        last_duration_ms: null,
        checks_passed: 0,
        checks_total: 4,
        evidence: ["docs/operations/OPERATOR_RUNBOOKS.md"],
        notes: ["Restore drill will capture live non-destructive evidence once the synthetic flow is executed."],
        details: {
          drill_mode: "non_destructive_live_probe",
          verified_store_count: 0,
          store_count: 4,
          stores: [],
        },
      },
    ],
  };
}

async function getFixtureOperatorTestsState(timestamp: string) {
  const sessionId = await getFixtureSessionId();
  const existing = FIXTURE_OPERATOR_TEST_STATES.get(sessionId);
  if (existing) {
    return existing;
  }
  const created = createFixtureOperatorTestsState(timestamp);
  FIXTURE_OPERATOR_TEST_STATES.set(sessionId, created);
  return created;
}

function fixturePresenceProfile(state: FixtureGovernorState) {
  return FIXTURE_PRESENCE_PROFILES[state.operator_presence];
}

function buildFixtureGovernorStateResponse(state: FixtureGovernorState, timestamp: string) {
  return {
    global_mode: state.global_mode,
    degraded_mode: state.degraded_mode,
    paused_lanes: [...state.paused_lanes],
    reason: state.reason,
    updated_at: state.updated_at ?? timestamp,
    updated_by: state.updated_by,
    operator_presence: state.operator_presence,
    presence_mode: state.presence_mode,
    presence_reason: state.presence_reason,
    presence_updated_at: state.presence_updated_at ?? timestamp,
    presence_updated_by: state.presence_updated_by,
    presence_signal_state: state.presence_signal_state,
    presence_signal_source: state.presence_signal_source,
    presence_signal_reason: state.presence_signal_reason,
    presence_signal_updated_at: state.presence_signal_updated_at ?? timestamp,
    presence_signal_updated_by: state.presence_signal_updated_by,
    release_tier: state.release_tier,
    tier_reason: state.tier_reason,
    tier_updated_at: state.tier_updated_at ?? timestamp,
    tier_updated_by: state.tier_updated_by,
  };
}

function buildFixturePromotionControls(timestamp: string, state: FixturePromotionState) {
  const candidateQueue = [
    {
      role_id: "frontier_supervisor",
      label: "Frontier supervisor",
      champion: "Claude",
      challengers: ["Codex", "Gemini", "Kimi", "GLM"],
      plane: "frontier_cloud",
    },
    {
      role_id: "coding_worker",
      label: "Coding worker",
      champion: "coding",
      challengers: ["coder", "worker"],
      plane: "local_worker",
    },
  ];
  const counts = state.records.reduce<Record<string, number>>((acc, record) => {
    acc[record.status] = (acc[record.status] ?? 0) + 1;
    return acc;
  }, {});
  return {
    generated_at: timestamp,
    status: state.records.length > 0 ? "live_partial" : "configured",
    tiers: ["offline_eval", "shadow", "sandbox", "canary", "production"],
    ritual: [
      "prepare candidate",
      "run offline eval and policy checks",
      "enable shadow mode",
      "promote to canary",
      "verify guardrail and operator outcomes",
      "promote to production or rollback",
      "record outcome in experiment ledger",
    ],
    counts,
    active_promotions: state.records.filter((record) => ["staged", "active", "held"].includes(record.status)),
    recent_promotions: state.records,
    recent_events: state.events,
    candidate_queue: candidateQueue,
    next_actions: state.records.length
      ? ["Advance the active frontier promotion after the next proving-ground pass."]
      : ["Stage a challenger candidate to activate governed promotion controls."],
  };
}

function buildFixtureRetirementControls(timestamp: string, state: FixtureRetirementState) {
  const candidateQueue = [
    {
      asset_class: "models",
      asset_id: "frontier_supervisor:Claude",
      label: "Frontier supervisor champion Claude",
      role_id: "frontier_supervisor",
      plane: "frontier_cloud",
      current_stage: "active",
    },
    {
      asset_class: "models",
      asset_id: "coding_worker:coding",
      label: "Coding worker champion coding",
      role_id: "coding_worker",
      plane: "local_worker",
      current_stage: "active",
    },
  ];
  const counts = state.records.reduce<Record<string, number>>((acc, record) => {
    acc[record.status] = (acc[record.status] ?? 0) + 1;
    return acc;
  }, {});
  return {
    generated_at: timestamp,
    status: state.records.length > 0 ? "live_partial" : "configured",
    asset_classes: ["models", "prompts", "policies", "routes", "agents", "eval corpora", "experiments"],
    stages: ["active", "deprecated", "retired_reference_only"],
    rule: "Retired assets remain historically visible but stop competing with active truth.",
    counts,
    active_retirements: state.records.filter((record) => ["staged", "active", "held"].includes(record.status)),
    recent_retirements: state.records,
    recent_events: state.events,
    candidate_queue: candidateQueue,
    next_actions: state.records.length
      ? ["Complete or roll back the active retirement rehearsal before retiring real assets."]
      : ["Stage a governed retirement rehearsal to activate live retirement controls."],
  };
}

function buildFixtureGovernorSnapshot(state: FixtureGovernorState, timestamp: string) {
  const signalState = state.presence_signal_state ?? "away";
  const effectiveState =
    state.presence_mode === "manual" ? state.operator_presence : signalState;
  const presence = FIXTURE_PRESENCE_PROFILES[effectiveState];
  const globalPaused = state.global_mode === "paused";

  return {
    generated_at: timestamp,
    status: "live",
    global_mode: state.global_mode,
    degraded_mode: state.degraded_mode,
    reason: state.reason,
    updated_at: state.updated_at ?? timestamp,
    updated_by: state.updated_by,
    lanes: FIXTURE_GOVERNOR_LANES.map((lane) => {
      const paused = globalPaused || state.paused_lanes.includes(lane.id);
      return {
        ...lane,
        paused,
        status: paused ? "paused" : "active",
      };
    }),
    capacity: {
      generated_at: timestamp,
      posture: "healthy",
      queue: {
        posture: "healthy",
        pending: 2,
        running: 1,
        max_concurrent: 2,
        failed: 0,
      },
      workspace: {
        broadcast_items: 4,
        capacity: 7,
        utilization: 0.57,
      },
      scheduler: {
        running: !globalPaused,
        enabled_count: 9,
      },
      local_compute: {
        sample_posture: "scheduler_projection_backed",
        scheduler_slot_count: 5,
        harvestable_scheduler_slot_count: 2,
        idle_harvest_slots_open: true,
        open_harvest_slots: [
          {
            id: "F:TP4",
            zone_id: "F",
            harvest_intent: "primary_sovereign_bulk",
            harvestable_gpu_count: 4,
            node_ids: ["foundry"],
          },
          {
            id: "W:1",
            zone_id: "W",
            harvest_intent: "creative_batch_support",
            harvestable_gpu_count: 1,
            node_ids: ["workshop"],
          },
        ],
        scheduler_queue_depth: 0,
        scheduler_source: "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
        scheduler_observed_at: timestamp,
      },
      provider_reserve: {
        posture: "healthy",
        constrained_count: 0,
      },
      active_time_windows: [
        {
          id: "morning_briefing",
          window: "06:30-08:30 local",
          protects: ["daily briefing", "workplan refresh", "notifications"],
          status: "configured",
        },
        {
          id: "quiet_hours",
          window: "22:00-06:00 local",
          protects: ["notifications", "quota harvesting"],
          status: "configured",
        },
      ],
      nodes: [
        {
          id: "foundry",
          alive: true,
          stale: false,
          max_gpu_util_pct: 71.0,
          healthy_models: 2,
          total_models: 2,
          load_1m: 1.2,
          ram_available_mb: 90112,
        },
        {
          id: "workshop",
          alive: true,
          stale: false,
          max_gpu_util_pct: 64.0,
          healthy_models: 2,
          total_models: 2,
          load_1m: 0.9,
          ram_available_mb: 74240,
        },
        {
          id: "dev",
          alive: true,
          stale: false,
          max_gpu_util_pct: 29.0,
          healthy_models: 2,
          total_models: 2,
          load_1m: 0.4,
          ram_available_mb: 31840,
        },
      ],
      recommendations: globalPaused
        ? ["Global automation pause is active; queued background work is held."]
        : ["Capacity posture is healthy across queue, nodes, and provider reserves."],
    },
    presence: {
      state: effectiveState,
      label: presence.label,
      automation_posture: presence.automation_posture,
      notification_posture: presence.notification_posture,
      approval_posture: presence.approval_posture,
      updated_at:
        state.presence_mode === "manual"
          ? state.presence_updated_at ?? timestamp
          : state.presence_signal_updated_at ?? timestamp,
      updated_by:
        state.presence_mode === "manual"
          ? state.presence_updated_by
          : state.presence_signal_updated_by,
      mode: state.presence_mode,
      configured_state: state.operator_presence,
      configured_label: FIXTURE_PRESENCE_PROFILES[state.operator_presence].label,
      signal_state: state.presence_signal_state,
      signal_source: state.presence_signal_source,
      signal_updated_at: state.presence_signal_updated_at ?? timestamp,
      signal_updated_by: state.presence_signal_updated_by,
      signal_fresh: true,
      signal_age_seconds: 0,
      effective_reason:
        state.presence_mode === "manual"
          ? state.presence_reason || "Manual operator presence override is active."
          : state.presence_signal_reason || "Fixture dashboard heartbeat is active.",
    },
    release_tier: {
      state: state.release_tier,
      available_tiers: ["offline_eval", "shadow", "sandbox", "canary", "production"],
      status: "configured",
      updated_at: state.tier_updated_at ?? timestamp,
      updated_by: state.tier_updated_by,
    },
    command_rights_version: "2026-03-12",
    control_stack: [
      { id: "agent-server", label: "Agent Server", status: "live" },
      { id: "task-engine", label: "Task Engine", status: "live" },
      { id: "scheduler", label: "Scheduler", status: "live" },
      { id: "capacity-governor", label: "Capacity Governor", status: "live" },
    ],
  };
}

function buildFixtureOperationsReadinessSnapshot(
  timestamp: string,
  operatorTestsState: FixtureOperatorTestsState,
  retirementState: FixtureRetirementState
) {
  return {
    generated_at: timestamp,
    status: "live_partial",
    runbooks: {
      status: "live_partial",
      items: [
        {
          id: "morning-review",
          label: "Morning review",
          description: "Review daily briefing, queue posture, alerts, and proving-ground recommendations.",
          cadence: "daily",
          related_surface: "/",
          evidence_flow_ids: ["scheduled_job_governance", "presence_tier"],
          support_status: "evidenced",
        },
        {
          id: "pause-or-resume-automation",
          label: "Pause or resume automation",
          description: "Use governor controls to pause global automation or bounded lanes, then confirm resumed posture.",
          cadence: "as-needed",
          related_surface: "/runs",
          evidence_flow_ids: ["pause_resume"],
          support_status: "evidenced",
        },
        {
          id: "provider-exhaustion-recovery",
          label: "Provider exhaustion recovery",
          description: "Inspect reserve posture, throttles, and downgrade order before resuming premium lanes.",
          cadence: "incident",
          related_surface: "/agents",
          evidence_flow_ids: ["provider_fallback", "economic_governance"],
          support_status: "evidenced",
        },
        {
          id: "stuck-queue-recovery",
          label: "Stuck queue recovery",
          description: "Use governor posture, scheduled-job state, and execution-run lineage to identify paused, deferred, or blocked work and restore forward progress safely.",
          cadence: "as-needed",
          related_surface: "/runs",
          evidence_flow_ids: ["stuck_queue_recovery", "pause_resume", "scheduled_job_governance"],
          support_status: "evidenced",
        },
        {
          id: "sovereign-routing-verification",
          label: "Sovereign routing verification",
          description: "Confirm refusal-sensitive or private work stayed on sovereign local lanes and that cloud-safe work remained eligible for frontier supervision.",
          cadence: "as-needed",
          related_surface: "/chat",
          evidence_flow_ids: ["sovereign_routing", "data_lifecycle"],
          support_status: "evidenced",
        },
        {
          id: "restore-drill",
          label: "Restore drill",
          description: "Validate recovery order for Redis, Qdrant, Neo4j, and deployment state.",
          cadence: "daily",
          related_surface: "/personal-data",
          evidence_flow_ids: ["restore_drill", "promotion_ladder"],
          support_status: "evidenced",
        },
        {
          id: "incident-review",
          label: "Incident review",
          description: "Use the operator stream, synthetic operator tests, and release-ladder posture to understand failures, retries, fallback behavior, and recovery decisions.",
          cadence: "as-needed",
          related_surface: "/inbox",
          evidence_flow_ids: ["incident_review", "provider_fallback", "restore_drill", "promotion_ladder"],
          support_status: "evidenced",
        },
      ],
    },
    backup_restore: {
      status: "live_partial",
      drill_mode: "non_destructive_live_probe",
      last_drill_at:
        operatorTestsState.flows.find((flow) => flow.id === "restore_drill")?.last_run_at ?? null,
      last_outcome:
        operatorTestsState.flows.find((flow) => flow.id === "restore_drill")?.last_outcome ?? null,
      verified_store_count:
        operatorTestsState.flows
          .find((flow) => flow.id === "restore_drill")
          ?.details?.verified_store_count ?? 0,
      store_count: 4,
      critical_stores: [
        {
          id: "redis_critical_state",
          label: "Redis critical state",
          drill_status: "verified",
          cadence: "weekly verification",
          restore_order: 1,
          verified: true,
          probe_status: "verified",
          probe_summary: "Redis ping and synthetic write/read/delete rehearsal succeeded.",
          last_drill_at:
            operatorTestsState.flows.find((flow) => flow.id === "restore_drill")?.last_run_at ?? null,
          last_outcome:
            operatorTestsState.flows.find((flow) => flow.id === "restore_drill")?.last_outcome ?? null,
        },
        {
          id: "qdrant_memory",
          label: "Qdrant vectors",
          drill_status: "verified",
          cadence: "monthly drill",
          restore_order: 2,
          verified: true,
          probe_status: "verified",
          probe_summary: "Qdrant collections endpoint is healthy and visible to the rehearsal flow.",
          last_drill_at:
            operatorTestsState.flows.find((flow) => flow.id === "restore_drill")?.last_run_at ?? null,
          last_outcome:
            operatorTestsState.flows.find((flow) => flow.id === "restore_drill")?.last_outcome ?? null,
        },
        {
          id: "neo4j_graph",
          label: "Neo4j graph",
          drill_status: "verified",
          cadence: "monthly drill",
          restore_order: 3,
          verified: true,
          probe_status: "verified",
          probe_summary: "Neo4j authenticated probe succeeded with a minimal read-only transaction.",
          last_drill_at:
            operatorTestsState.flows.find((flow) => flow.id === "restore_drill")?.last_run_at ?? null,
          last_outcome:
            operatorTestsState.flows.find((flow) => flow.id === "restore_drill")?.last_outcome ?? null,
        },
        {
          id: "dashboard_agent_deploy_state",
          label: "Dashboard and agent deployment state",
          drill_status: "verified",
          cadence: "per release",
          restore_order: 4,
          verified: true,
          probe_status: "verified",
          probe_summary: "Agent and dashboard deployment surfaces are reachable for ordered recovery.",
          last_drill_at:
            operatorTestsState.flows.find((flow) => flow.id === "restore_drill")?.last_run_at ?? null,
          last_outcome:
            operatorTestsState.flows.find((flow) => flow.id === "restore_drill")?.last_outcome ?? null,
        },
      ],
    },
    release_ritual: {
      status: "live_partial",
      tiers: ["offline_eval", "shadow", "sandbox", "canary", "production"],
      ritual: ["prepare", "canary", "verify", "promote", "revert_if_needed", "record_outcome"],
    },
    deprecation_retirement: {
      status:
        operatorTestsState.flows.find((flow) => flow.id === "retirement_policy")?.last_outcome === "passed"
          ? "live_partial"
          : "configured",
      asset_classes: ["models", "prompts", "policies", "routes", "agents", "eval corpora", "experiments"],
      stages: ["active", "deprecated", "retired_reference_only"],
      rule: "Retired assets remain historically visible but stop competing with active truth.",
      recent_retirement_count: retirementState.records.length,
      active_retirement_count: retirementState.records.filter((record) => ["staged", "active", "held"].includes(record.status)).length,
      last_rehearsal_at:
        operatorTestsState.flows.find((flow) => flow.id === "retirement_policy")?.last_run_at ?? null,
      last_outcome:
        operatorTestsState.flows.find((flow) => flow.id === "retirement_policy")?.last_outcome ?? null,
      recent_retirements: retirementState.records,
    },
    economic_governance: {
      status: "live_partial",
      premium_reserve_lanes: ["frontier_cloud", "interactive_review"],
      automatic_spend_lanes: ["repo_audit_harvest", "benchmark_cycle"],
      approval_required_lanes: ["high_cost_frontier_review", "extended_coding_supervision"],
      downgrade_order: ["harvest_jobs", "background_research", "extended_review", "interactive_frontier"],
    },
    data_lifecycle: {
      status: "live_partial",
      classes: [
        {
          id: "ephemeral_events",
          label: "Ephemeral events",
          retention: "hours",
          sovereign_only: false,
          cloud_allowed: true,
        },
        {
          id: "operational_runs",
          label: "Operational runs",
          retention: "30d",
          sovereign_only: false,
          cloud_allowed: false,
        },
        {
          id: "sovereign_content",
          label: "Sovereign content",
          retention: "operator controlled",
          sovereign_only: true,
          cloud_allowed: false,
        },
        {
          id: "eval_corpora",
          label: "Eval corpora",
          retention: "versioned",
          sovereign_only: true,
          cloud_allowed: false,
        },
      ],
    },
    tool_permissions: {
      status: "live_partial",
      default_mode: "governor_mediated",
      subjects: [
        {
          subject: "frontier_meta_lane",
          mode: "plan_review_only",
          deny: ["shell", "filesystem_write", "deployment_mutation"],
        },
        {
          subject: "sovereign_meta_lane",
          mode: "plan_review_only",
          deny: ["cloud_handoff", "deployment_mutation"],
        },
        {
          subject: "coding-agent",
          mode: "scoped_execution",
          allow: ["read_file", "write_file", "run_command"],
        },
      ],
    },
    synthetic_operator_tests: {
      status:
        operatorTestsState.last_outcome === "failed"
          ? "degraded"
          : operatorTestsState.last_run_at
            ? "live_partial"
            : "configured",
      last_outcome: operatorTestsState.last_outcome,
      last_run_at: operatorTestsState.last_run_at,
      flow_count: operatorTestsState.flows.length,
      flows: operatorTestsState.flows,
    },
  };
}

async function buildFixtureAgentResponse(path: string, init: RequestInit | undefined) {
  const method = (init?.method ?? "GET").toUpperCase();
  const payload = parseFixtureBody(init?.body);
  const timestamp = FIXTURE_BASE_TIME;
  const isoMinutesBefore = (minutesBefore: number) =>
    new Date(new Date(timestamp).getTime() - minutesBefore * 60_000).toISOString();
  const requestUrl = new URL(`http://fixture${path}`);
  const limitParam = Number.parseInt(requestUrl.searchParams.get("limit") ?? "", 10);
  const limit = Number.isNaN(limitParam) ? null : limitParam;
  const agent = requestUrl.searchParams.get("agent");
  const basePath = path.split("?")[0];
  const governorState = await getFixtureGovernorState();
  const operatorTestsState = await getFixtureOperatorTestsState(timestamp);
  const promotionState = await getFixturePromotionState(timestamp);
  const retirementState = await getFixtureRetirementState();

  const buildFixtureProjectPacket = (projectId: string) => ({
    id: projectId,
    name:
      projectId === "athanor"
        ? "Athanor"
        : projectId === "eoq"
          ? "Empire of Broken Queens"
          : projectId === "kindred"
            ? "Kindred"
            : projectId,
    stage:
      projectId === "athanor"
        ? "active_build"
        : projectId === "media"
          ? "governed_domain"
          : "scaffold",
    template:
      projectId === "athanor"
        ? "internal_operator_app"
        : projectId === "media"
          ? "domain_surface"
          : "public_product_app",
    class: projectId === "media" ? "domain" : "tenant",
    visibility: projectId === "kindred" ? "pilot" : "private",
    sensitivity: projectId === "eoq" ? "adult_sensitive" : "private",
    runtime_target: projectId === "kindred" ? "vercel" : "cluster",
    deploy_target: projectId === "kindred" ? "vercel" : "cluster",
    workspace_root:
      projectId === "athanor" ? "C:\\Athanor" : `C:\\Athanor\\projects\\${projectId}`,
    primary_route: projectId === "media" ? "/media" : "/projects",
    owner_domain: projectId === "media" ? "media" : "product_foundry",
    operators: ["Shaun", "Claude"],
    agents:
      projectId === "media"
        ? ["media-agent", "stash-agent"]
        : ["coding-agent", "research-agent", "knowledge-agent"],
    acceptance_bundle:
      projectId === "athanor"
        ? [
            "Durable operator work surfaces",
            "Registry-backed runtime authority",
            "Foundry packet and deploy candidate path",
          ]
        : ["Packet-approved scaffold", "Rollback evidence before promotion"],
    rollback_contract:
      projectId === "athanor"
        ? "Revert candidate promotion and restore the prior operator packet snapshot."
        : "Restore the prior scaffold candidate and invalidate the failed promotion.",
    maintenance_cadence: projectId === "athanor" ? "weekly" : "monthly",
    metadata: {
      source: "dashboard_fixture",
      status: projectId === "athanor" ? "live" : "pilot",
    },
    created_at: new Date(timestamp).getTime() / 1000 - 14 * 24 * 60 * 60,
    updated_at: new Date(timestamp).getTime() / 1000 - 25 * 60,
  });

  const buildFixtureArchitecturePacket = (projectId: string) => ({
    project_id: projectId,
    service_shape: {
      app:
        projectId === "athanor" ? "nextjs-operator" : projectId === "kindred" ? "public-product-app" : "service",
      runtime: projectId === "kindred" ? "vercel" : "cluster",
    },
    data_contracts:
      projectId === "athanor"
        ? ["operator-work snapshots", "registry-backed governance"]
        : ["deploy candidate", "public-edge configuration"],
    auth_boundary:
      projectId === "kindred"
        ? { operator_auth_shared: false, product_auth: "separate" }
        : { operator_auth_shared: true, product_auth: "n/a" },
    deploy_shape:
      projectId === "kindred"
        ? { primary: "preview-staging-production", rollback: "instant" }
        : { primary: "cluster", rollback: "config snapshot" },
    risk_notes:
      projectId === "athanor"
        ? ["Do not widen autonomy until launch blockers clear."]
        : ["Promotion blocked until rollback evidence is recorded."],
    test_plan:
      projectId === "athanor"
        ? ["durable restart drill", "operator work regression suite"]
        : ["preview smoke", "promotion rollback drill"],
    rollback_notes:
      projectId === "athanor"
        ? ["Restore prior packet", "Re-run operator smoke suite"]
        : ["Rollback to previous candidate", "Verify preview health"],
    metadata: { source: "dashboard_fixture" },
    approved_at: new Date(timestamp).getTime() / 1000 - 4 * 24 * 60 * 60,
    created_at: new Date(timestamp).getTime() / 1000 - 10 * 24 * 60 * 60,
    updated_at: new Date(timestamp).getTime() / 1000 - 55 * 60,
  });

  const buildFixtureFoundryRuns = (projectId: string) => [
    {
      id: `${projectId}-foundry-run-1`,
      project_id: projectId,
      slice_id: `${projectId}-slice-1`,
      execution_run_id: `run-${projectId}-1`,
      status: "running",
      summary: "Executing the current slice with durable run lineage enabled.",
      artifact_refs: ["artifact://foundry/log", "artifact://foundry/review"],
      review_refs: ["review://launch/readiness"],
      metadata: { source: "dashboard_fixture" },
      created_at: new Date(timestamp).getTime() / 1000 - 95 * 60,
      updated_at: new Date(timestamp).getTime() / 1000 - 6 * 60,
      completed_at: 0,
    },
    {
      id: `${projectId}-foundry-run-2`,
      project_id: projectId,
      slice_id: `${projectId}-slice-0`,
      execution_run_id: `run-${projectId}-0`,
      status: "completed",
      summary: "Previous slice completed with acceptance evidence attached.",
      artifact_refs: ["artifact://foundry/smoke"],
      review_refs: ["review://launch/acceptance"],
      metadata: { source: "dashboard_fixture" },
      created_at: new Date(timestamp).getTime() / 1000 - 480 * 60,
      updated_at: new Date(timestamp).getTime() / 1000 - 420 * 60,
      completed_at: new Date(timestamp).getTime() / 1000 - 420 * 60,
    },
  ];

  const buildFixtureExecutionSlices = (projectId: string) => [
    {
      id: `${projectId}-slice-1`,
      project_id: projectId,
      owner_agent: "coding-agent",
      lane: projectId === "kindred" ? "codex_cloudsafe" : "sovereign_coder",
      base_sha: "abc1234",
      worktree_path: `C:\\Athanor\\worktrees\\${projectId}-slice-1`,
      acceptance_target: "packet acceptance bundle",
      status: "active",
      metadata: { source: "dashboard_fixture" },
      created_at: new Date(timestamp).getTime() / 1000 - 120 * 60,
      updated_at: new Date(timestamp).getTime() / 1000 - 25 * 60,
    },
    {
      id: `${projectId}-slice-0`,
      project_id: projectId,
      owner_agent: "coding-agent",
      lane: projectId === "kindred" ? "codex_cloudsafe" : "sovereign_coder",
      base_sha: "def5678",
      worktree_path: `C:\\Athanor\\worktrees\\${projectId}-slice-0`,
      acceptance_target: "previous release candidate",
      status: "completed",
      metadata: { source: "dashboard_fixture" },
      created_at: new Date(timestamp).getTime() / 1000 - 520 * 60,
      updated_at: new Date(timestamp).getTime() / 1000 - 420 * 60,
    },
  ];

  const buildFixtureDeployments = (projectId: string) => [
    {
      id: `${projectId}-candidate-1`,
      project_id: projectId,
      channel: projectId === "kindred" ? "public_staging" : "internal_preview",
      artifact_refs: ["artifact://deploy/build", "artifact://deploy/smoke"],
      env_contract: {
        runtime: projectId === "kindred" ? "vercel" : "cluster",
        secrets_verified: true,
      },
      smoke_results: {
        status: "passed",
        verified_at: isoMinutesBefore(40),
      },
      rollback_target: {
        type: projectId === "kindred" ? "vercel-rollback" : "cluster-snapshot",
        ref: `${projectId}-rollback-anchor`,
      },
      promotion_status: "pending",
      metadata: { source: "dashboard_fixture" },
      created_at: new Date(timestamp).getTime() / 1000 - 75 * 60,
      updated_at: new Date(timestamp).getTime() / 1000 - 20 * 60,
      promoted_at: 0,
    },
    {
      id: `${projectId}-candidate-0`,
      project_id: projectId,
      channel: projectId === "kindred" ? "public_preview" : "internal_preview",
      artifact_refs: ["artifact://deploy/build-previous"],
      env_contract: {
        runtime: projectId === "kindred" ? "vercel" : "cluster",
      },
      smoke_results: {
        status: "passed",
        verified_at: isoMinutesBefore(360),
      },
      rollback_target: {
        type: projectId === "kindred" ? "vercel-rollback" : "cluster-snapshot",
        ref: `${projectId}-rollback-anchor-previous`,
      },
      promotion_status: "promoted",
      metadata: { source: "dashboard_fixture" },
      created_at: new Date(timestamp).getTime() / 1000 - 420 * 60,
      updated_at: new Date(timestamp).getTime() / 1000 - 360 * 60,
      promoted_at: new Date(timestamp).getTime() / 1000 - 360 * 60,
    },
  ];

  const buildFixtureRollbacks = (projectId: string) => [
    {
      id: `${projectId}-rollback-1`,
      project_id: projectId,
      candidate_id: `${projectId}-candidate-0`,
      reason: "Rollback anchor preserved from the last successful promotion.",
      rollback_target: {
        type: projectId === "kindred" ? "vercel-rollback" : "cluster-snapshot",
        ref: `${projectId}-rollback-anchor-previous`,
      },
      status: "recorded",
      metadata: {
        channel: projectId === "kindred" ? "public_preview" : "internal_preview",
        source: "dashboard_fixture",
      },
      created_at: new Date(timestamp).getTime() / 1000 - 355 * 60,
    },
  ];

  const buildFixtureMaintenanceRuns = (projectId: string) => [
    {
      id: `${projectId}-maintenance-1`,
      project_id: projectId,
      kind: "smoke",
      trigger: "post-promotion",
      status: "completed",
      evidence_ref: "artifact://maintenance/smoke",
      metadata: { source: "dashboard_fixture" },
      created_at: new Date(timestamp).getTime() / 1000 - 50 * 60,
      updated_at: new Date(timestamp).getTime() / 1000 - 35 * 60,
      completed_at: new Date(timestamp).getTime() / 1000 - 35 * 60,
    },
  ];

  if (method === "GET" && basePath === "/v1/tasks") {
    const tasks = getFixtureAgentTasks({ agent, limit });
    return {
      tasks,
      count: tasks.length,
    };
  }

  if (method === "GET" && basePath === "/v1/operator/inbox") {
    const status = requestUrl.searchParams.get("status");
    const items = [
      {
        id: "inbox-fixture-1",
        kind: "approval_request",
        severity: 3,
        status: "new",
        source: "system",
        title: "Approve durable-state rollout follow-up",
        description: "The next control-plane tranche is waiting on operator review.",
        requires_decision: true,
        decision_type: "approval",
        snooze_until: 0,
        created_at: new Date(timestamp).getTime() / 1000 - 15 * 60,
        updated_at: new Date(timestamp).getTime() / 1000 - 15 * 60,
        resolved_at: 0,
      },
      {
        id: "inbox-fixture-2",
        kind: "blocked_run",
        severity: 2,
        status: "acknowledged",
        source: "foundry",
        title: "Review blocked rollout note",
        description: "A follow-up run is waiting on a dashboard-side confirmation.",
        requires_decision: false,
        decision_type: "",
        snooze_until: 0,
        created_at: new Date(timestamp).getTime() / 1000 - 90 * 60,
        updated_at: new Date(timestamp).getTime() / 1000 - 50 * 60,
        resolved_at: 0,
      },
      {
        id: "inbox-fixture-3",
        kind: "daily_brief",
        severity: 1,
        status: "snoozed",
        source: "planner",
        title: "Morning brief parked",
        description: "Deferred until the next work block.",
        requires_decision: false,
        decision_type: "",
        snooze_until: new Date(new Date(timestamp).getTime() + 30 * 60_000).getTime() / 1000,
        created_at: new Date(timestamp).getTime() / 1000 - 3 * 60 * 60,
        updated_at: new Date(timestamp).getTime() / 1000 - 20 * 60,
        resolved_at: 0,
      },
    ].filter((item) => !status || item.status === status);
    const trimmed = limit ? items.slice(0, limit) : items;
      return { items: trimmed, count: trimmed.length };
    }

  if (method === "GET" && basePath === "/v1/operator/ideas") {
      const status = requestUrl.searchParams.get("status");
      const ideas = [
        {
          id: "idea-fixture-1",
          title: "Foundry promotion cockpit",
          note: "Add a promotion lane that records rollback targets before the operator can advance a candidate.",
          tags: ["foundry", "launch"],
          source: "operator",
          confidence: 0.91,
          energy_class: "focused",
          scope_guess: "project",
          status: "candidate",
          next_review_at: 0,
          promoted_project_id: "",
          created_at: new Date(timestamp).getTime() / 1000 - 180 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 35 * 60,
        },
        {
          id: "idea-fixture-2",
          title: "Autonomy blocker digest",
          note: "Group provider auth, durable posture, and next-phase blockers into one operator-facing surface.",
          tags: ["autonomy", "ops"],
          source: "planner",
          confidence: 0.74,
          energy_class: "quick",
          scope_guess: "global",
          status: "sprout",
          next_review_at: new Date(new Date(timestamp).getTime() + 4 * 60 * 60_000).getTime() / 1000,
          promoted_project_id: "",
          created_at: new Date(timestamp).getTime() / 1000 - 420 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 95 * 60,
        },
        {
          id: "idea-fixture-3",
          title: "Provider lane repair rehearsal",
          note: "Capture the exact evidence bundle after the next VAULT auth pass.",
          tags: ["providers"],
          source: "research-agent",
          confidence: 0.63,
          energy_class: "admin",
          scope_guess: "domain",
          status: "seed",
          next_review_at: 0,
          promoted_project_id: "",
          created_at: new Date(timestamp).getTime() / 1000 - 960 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 510 * 60,
        },
      ].filter((idea) => !status || idea.status === status);
      const trimmed = limit ? ideas.slice(0, limit) : ideas;
      return { ideas: trimmed, count: trimmed.length };
    }

  if (method === "GET" && basePath === "/v1/operator/todos") {
    const status = requestUrl.searchParams.get("status");
    const todos = [
      {
        id: "todo-fixture-1",
        title: "Review next migration tranche",
        description: "Validate the next durable operator-work rollout before widening scope.",
        category: "ops",
        scope_type: "global",
        scope_id: "athanor",
        priority: 3,
        status: "open",
        energy_class: "focused",
        created_at: new Date(timestamp).getTime() / 1000 - 2 * 60 * 60,
        updated_at: new Date(timestamp).getTime() / 1000 - 2 * 60 * 60,
        completed_at: 0,
      },
      {
        id: "todo-fixture-2",
        title: "Confirm provider auth repair window",
        description: "Coordinate the next VAULT maintenance pass.",
        category: "approval",
        scope_type: "global",
        scope_id: "athanor",
        priority: 4,
        status: "ready",
        energy_class: "quick",
        created_at: new Date(timestamp).getTime() / 1000 - 5 * 60 * 60,
        updated_at: new Date(timestamp).getTime() / 1000 - 75 * 60,
        completed_at: 0,
      },
      {
        id: "todo-fixture-3",
        title: "Capture dashboard fixture follow-up",
        description: "This one is parked until the operator pages settle.",
        category: "maintenance",
        scope_type: "global",
        scope_id: "athanor",
        priority: 2,
        status: "someday",
        energy_class: "quick",
        created_at: new Date(timestamp).getTime() / 1000 - 24 * 60 * 60,
        updated_at: new Date(timestamp).getTime() / 1000 - 24 * 60 * 60,
        completed_at: 0,
      },
    ].filter((todo) => !status || todo.status === status);
      const trimmed = limit ? todos.slice(0, limit) : todos;
      return { todos: trimmed, count: trimmed.length };
    }

  if (method === "GET" && basePath === "/v1/operator/backlog") {
      const status = requestUrl.searchParams.get("status");
      const ownerAgent = requestUrl.searchParams.get("owner_agent");
      const backlog = [
        {
          id: "backlog-fixture-1",
          title: "Finish durable execution run ledger",
          prompt: "Extend the durable state layer so task projections become canonical execution runs with attempts and steps.",
          owner_agent: "coding-agent",
          support_agents: ["knowledge-agent"],
          scope_type: "project",
          scope_id: "athanor",
          work_class: "migration",
          priority: 5,
          status: "ready",
          approval_mode: "none",
          dispatch_policy: "planner_eligible",
          preconditions: ["schema bootstrap landed"],
          blocking_reason: "",
          created_at: new Date(timestamp).getTime() / 1000 - 260 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 18 * 60,
          completed_at: 0,
        },
        {
          id: "backlog-fixture-2",
          title: "Rehearse degraded mode banner and suppression",
          prompt: "Verify the dashboard and runtime both suppress nonessential dispatch when degraded mode is active.",
          owner_agent: "general-assistant",
          support_agents: ["coding-agent"],
          scope_type: "global",
          scope_id: "athanor",
          work_class: "ops_audit",
          priority: 4,
          status: "blocked",
          approval_mode: "operator",
          dispatch_policy: "manual_only",
          preconditions: ["mode transitions live"],
          blocking_reason: "Awaiting the governance slice.",
          created_at: new Date(timestamp).getTime() / 1000 - 520 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 62 * 60,
          completed_at: 0,
        },
        {
          id: "backlog-fixture-3",
          title: "Public-edge rollout packet",
          prompt: "Prepare the Vercel rollout defaults and rollback evidence for the next public product.",
          owner_agent: "research-agent",
          support_agents: ["coding-agent"],
          scope_type: "project",
          scope_id: "eoq",
          work_class: "research",
          priority: 3,
          status: "waiting_approval",
          approval_mode: "admin",
          dispatch_policy: "manual_only",
          preconditions: [],
          blocking_reason: "",
          created_at: new Date(timestamp).getTime() / 1000 - 800 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 120 * 60,
          completed_at: 0,
        },
      ].filter((item) => (!status || item.status === status) && (!ownerAgent || item.owner_agent === ownerAgent));
      const trimmed = limit ? backlog.slice(0, limit) : backlog;
      return { backlog: trimmed, count: trimmed.length };
    }

  if (method === "GET" && basePath === "/v1/operator/runs") {
      const status = requestUrl.searchParams.get("status");
      const agentFilter = requestUrl.searchParams.get("agent");
      const runs = [
        {
          id: "run-fixture-1",
          task_id: "task-fixture-1",
          backlog_id: "backlog-fixture-1",
          agent_id: "coding-agent",
          workload_class: "migration",
          provider_lane: "athanor_local",
          runtime_lane: "coding-agent",
          policy_class: "private",
          status: "running",
          summary: "Durable execution ledger write-through is in progress.",
          created_at: new Date(timestamp).getTime() / 1000 - 40 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 4 * 60,
          completed_at: 0,
          step_count: 4,
          approval_pending: false,
          latest_attempt: {
            id: "run-fixture-1:attempt:0",
            runtime_host: "foundry",
            status: "running",
            heartbeat_at: new Date(timestamp).getTime() / 1000 - 60,
          },
          approvals: [],
        },
        {
          id: "run-fixture-2",
          task_id: "task-fixture-2",
          backlog_id: "backlog-fixture-3",
          agent_id: "research-agent",
          workload_class: "research",
          provider_lane: "frontier_cloud",
          runtime_lane: "research-agent",
          policy_class: "cloud_safe",
          status: "waiting_approval",
          summary: "Public-edge rollout packet is waiting on operator approval before continuing.",
          created_at: new Date(timestamp).getTime() / 1000 - 130 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 12 * 60,
          completed_at: 0,
          step_count: 2,
          approval_pending: true,
          latest_attempt: {
            id: "run-fixture-2:attempt:0",
            runtime_host: "frontier-cloud",
            status: "waiting_approval",
            heartbeat_at: new Date(timestamp).getTime() / 1000 - 12 * 60,
          },
          approvals: [{ id: "approval-fixture-1", status: "pending", privilege_class: "admin" }],
        },
        {
          id: "run-fixture-3",
          task_id: "task-fixture-3",
          backlog_id: "",
          agent_id: "general-assistant",
          workload_class: "operator_briefing",
          provider_lane: "athanor_local",
          runtime_lane: "general-assistant",
          policy_class: "private",
          status: "completed",
          summary: "Morning operator summary completed with durable snapshot evidence.",
          created_at: new Date(timestamp).getTime() / 1000 - 360 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 300 * 60,
          completed_at: new Date(timestamp).getTime() / 1000 - 300 * 60,
          step_count: 3,
          approval_pending: false,
          latest_attempt: {
            id: "run-fixture-3:attempt:0",
            runtime_host: "foundry",
            status: "completed",
            heartbeat_at: new Date(timestamp).getTime() / 1000 - 300 * 60,
          },
          approvals: [],
        },
        {
          id: "run-fixture-4",
          task_id: "task-fixture-4",
          backlog_id: "backlog-fixture-4",
          agent_id: "general-assistant",
          workload_class: "operator_briefing",
          provider_lane: "athanor_local",
          runtime_lane: "general-assistant",
          policy_class: "private",
          status: "queued",
          summary: "Prepare the next operator brief from canonical inbox and run surfaces.",
          created_at: new Date(timestamp).getTime() / 1000 - 8 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 2 * 60,
          completed_at: 0,
          step_count: 0,
          approval_pending: false,
          latest_attempt: null,
          approvals: [],
        },
      ].filter((run) => (!status || run.status === status) && (!agentFilter || run.agent_id === agentFilter));
      const trimmed = limit ? runs.slice(0, limit) : runs;
      return { runs: trimmed, count: trimmed.length };
    }

  if (method === "GET" && basePath === "/v1/operator/approvals") {
      const status = requestUrl.searchParams.get("status");
      const approvals = [
        {
          id: "approval-fixture-1",
          related_run_id: "run-fixture-2",
          related_attempt_id: "run-fixture-2:attempt:0",
          related_task_id: "task-fixture-2",
          requested_action: "approve_task",
          privilege_class: "admin",
          reason: "Public-edge rollout packet needs operator approval before continuing.",
          status: "pending",
          requested_at: new Date(timestamp).getTime() / 1000 - 18 * 60,
          decided_at: 0,
          decided_by: "",
          task_prompt: "Promote the public-edge rollout packet after smoke evidence is attached.",
          task_agent_id: "coding-agent",
          task_priority: "high",
          task_status: "pending_approval",
          task_created_at: new Date(timestamp).getTime() / 1000 - 26 * 60,
          metadata: {
            source: "dashboard_fixture",
            scope_id: "eoq",
          },
        },
      ].filter((approval) => !status || approval.status === status);
      const trimmed = limit ? approvals.slice(0, limit) : approvals;
      return { approvals: trimmed, count: trimmed.length };
    }

  if (method === "POST" && /\/v1\/operator\/approvals\/[^/]+\/approve$/.test(path)) {
      return {
        ok: true,
        fixture: true,
        status: "approved",
        approval: {
          id: path.split("/").at(-2),
          status: "approved",
          decided_by: "dashboard-operator",
          decided_at: new Date(timestamp).getTime() / 1000,
        },
        timestamp,
      };
    }

  if (method === "POST" && /\/v1\/operator\/approvals\/[^/]+\/reject$/.test(path)) {
      return {
        ok: true,
        fixture: true,
        status: "rejected",
        approval: {
          id: path.split("/").at(-2),
          status: "rejected",
          decided_by: "dashboard-operator",
          decided_at: new Date(timestamp).getTime() / 1000,
        },
        timestamp,
      };
    }

  if (method === "GET" && basePath === "/v1/operator/governance") {
      return {
        current_mode: {
          id: "mode-constrained-fixture",
          mode: "constrained",
          entered_at: new Date(timestamp).getTime() / 1000 - 45 * 60,
          entered_by: "operator",
          trigger: "attention_breach",
          exit_conditions: "Clear attention breaches for 15 minutes.",
          notes: "Fixture governance posture while the launch-readiness tranche is in flight.",
          metadata: {},
        },
        mode_history: [
          {
            id: "mode-constrained-fixture",
            mode: "constrained",
            entered_at: new Date(timestamp).getTime() / 1000 - 45 * 60,
            entered_by: "operator",
            trigger: "attention_breach",
            exit_conditions: "Clear attention breaches for 15 minutes.",
            notes: "Fixture governance posture while the launch-readiness tranche is in flight.",
            metadata: {},
          },
          {
            id: "mode-normal-fixture",
            mode: "normal",
            entered_at: new Date(timestamp).getTime() / 1000 - 8 * 60 * 60,
            entered_by: "system",
            trigger: "registry_seed",
            exit_conditions: "",
            notes: "Seeded default mode.",
            metadata: {},
          },
        ],
        attention_budgets: [
          {
            id: "general-assistant",
            scope_type: "agent",
            scope_id: "general-assistant",
            daily_limit: 12,
            urgent_bypass: [],
            used_today: 8,
            status: "active",
            last_reset_at: new Date(timestamp).getTime() / 1000 - 6 * 60 * 60,
            metadata: {},
            created_at: new Date(timestamp).getTime() / 1000 - 30 * 24 * 60 * 60,
            updated_at: new Date(timestamp).getTime() / 1000 - 60 * 60,
          },
          {
            id: "home-agent",
            scope_type: "agent",
            scope_id: "home-agent",
            daily_limit: 12,
            urgent_bypass: ["security_alert", "security_action_requested"],
            used_today: 3,
            status: "active",
            last_reset_at: new Date(timestamp).getTime() / 1000 - 6 * 60 * 60,
            metadata: {},
            created_at: new Date(timestamp).getTime() / 1000 - 30 * 24 * 60 * 60,
            updated_at: new Date(timestamp).getTime() / 1000 - 60 * 60,
          },
        ],
        attention_posture: {
          open_inbox_count: 11,
          urgent_inbox_count: 4,
          pending_approval_count: 1,
          blocked_run_count: 3,
          stale_blocked_run_count: 3,
          recommended_mode: "constrained",
          breaches: [
            "attention:open_inbox",
            "attention:urgent_inbox",
            "attention:stale_blocked_runs",
          ],
          by_status: {
            new: 1,
            acknowledged: 1,
            snoozed: 1,
          },
        },
        core_change_windows: [
          {
            id: "core-window-first-weekend",
            label: "First Weekend Window",
            schedule: "first_weekend",
            start_local: "Saturday 00:00",
            end_local: "Sunday 23:59",
            allowed_change_classes: ["core_contract", "schema_migration", "runtime_cutover", "validator_repair"],
            status: "live",
            notes: "Default monthly core change window.",
            metadata: {},
            created_at: new Date(timestamp).getTime() / 1000 - 30 * 24 * 60 * 60,
            updated_at: new Date(timestamp).getTime() / 1000 - 24 * 60 * 60,
          },
        ],
        launch_posture: {
          activation_state: "full_system_active",
          current_phase_id: "full_system_phase_3",
          current_phase_status: "active",
          next_phase_id: null,
          next_phase_status: null,
          current_phase_blockers: [],
          next_phase_blockers: [],
          provider_evidence: {
            path: "C:\\Athanor\\reports\\truth-inventory\\provider-usage-evidence.json",
            exists: true,
            capture_count: 4,
            latest_provider_capture_count: 4,
            observed_count: 3,
            auth_failed_count: 1,
            request_failed_count: 0,
            provider_count: 16,
            weak_lane_count: 2,
            weak_provider_ids: ["moonshot_kimi", "openai_api"],
            weak_posture_counts: {
              live_burn_observed_cost_unverified: 1,
              vault_provider_specific_auth_failed: 1,
            },
            capture_status_counts: {
              observed: 3,
              auth_failed: 1,
            },
            auth_failed_provider_ids: ["openai_api"],
            cost_unverified_provider_ids: ["moonshot_kimi"],
            supported_tool_unverified_provider_ids: [],
            verification_queue: [
              {
                provider_id: "moonshot_kimi",
                label: "Kimi Code",
                evidence_posture: "live_burn_observed_cost_unverified",
                pricing_truth_label: "flat_rate_unverified",
                next_verification:
                  "Verify the subscribed monthly tier or billing surface for `Kimi Code` from a current operator-visible source.",
                verification_steps: [
                  "Verify the subscribed monthly tier or billing surface for `Kimi Code` from a current operator-visible source.",
                  "Keep this lane cost-unverified until the billing tier is proven from a current runtime-visible or operator-visible surface.",
                ],
                capture_status: null,
                capture_observed_at: null,
                missing_env_names: [],
                present_env_names: [],
                priority: 0,
              },
              {
                provider_id: "openai_api",
                label: "OpenAI API",
                evidence_posture: "vault_provider_specific_auth_failed",
                pricing_truth_label: "metered_api",
                next_verification:
                  "Use the VAULT LiteLLM repair packet to rotate OPENAI_API_KEY, recreate or redeploy `litellm`, then re-probe served model `gpt`.",
                verification_steps: [
                  "Use the VAULT LiteLLM repair packet to rotate OPENAI_API_KEY, recreate or redeploy `litellm`, then re-probe served model `gpt`.",
                  "Do not treat `OpenAI API` as provider-specifically proven until the auth failure is gone and a successful completion is recorded.",
                ],
                capture_status: "auth_failed",
                capture_observed_at: timestamp,
                missing_env_names: [],
                present_env_names: ["OPENAI_API_KEY"],
                priority: 2,
              },
            ],
            vault_litellm_env_audit_path:
              "C:\\Athanor\\reports\\truth-inventory\\vault-litellm-env-audit.json",
            vault_litellm_env_audit_exists: true,
          },
          required_runbook_count: 10,
          registered_runbook_count: 10,
          missing_runbook_ids: [],
          launch_blockers: [],
          issues: [],
        },
        launch_blockers: [],
        issues: [
          "attention:open_inbox",
          "attention:urgent_inbox",
          "attention:stale_blocked_runs",
        ],
        launch_ready: true,
      };
    }

  if (method === "GET" && basePath === "/v1/operator/system-mode") {
      return {
        current_mode: {
          id: "mode-constrained-fixture",
          mode: "constrained",
          entered_at: new Date(timestamp).getTime() / 1000 - 45 * 60,
          entered_by: "operator",
          trigger: "attention_breach",
          exit_conditions: "Clear attention breaches for 15 minutes.",
          notes: "Fixture governance posture while the launch-readiness tranche is in flight.",
          metadata: {},
        },
        attention_posture: {
          open_inbox_count: 11,
          urgent_inbox_count: 4,
          pending_approval_count: 1,
          blocked_run_count: 3,
          stale_blocked_run_count: 3,
          recommended_mode: "constrained",
          breaches: [
            "attention:open_inbox",
            "attention:urgent_inbox",
            "attention:stale_blocked_runs",
          ],
          by_status: {
            new: 1,
            acknowledged: 1,
            snoozed: 1,
          },
        },
      };
    }

  if (method === "POST" && basePath === "/v1/operator/system-mode") {
      return {
        status: "updated",
        current_mode: {
          id: "mode-updated-fixture",
          mode: typeof payload?.mode === "string" && payload.mode.length > 0 ? payload.mode : "normal",
          entered_at: new Date(timestamp).getTime() / 1000,
          entered_by: typeof payload?.actor === "string" && payload.actor.length > 0 ? payload.actor : "dashboard-operator",
          trigger: typeof payload?.trigger === "string" ? payload.trigger : "",
          exit_conditions: typeof payload?.exit_conditions === "string" ? payload.exit_conditions : "",
          notes: typeof payload?.notes === "string" ? payload.notes : "",
          metadata: typeof payload?.metadata === "object" && payload?.metadata ? payload.metadata : {},
        },
      };
    }

  if (method === "GET" && basePath === "/v1/operator/attention-budgets") {
      const budgets = [
        {
          id: "general-assistant",
          scope_type: "agent",
          scope_id: "general-assistant",
          daily_limit: 12,
          urgent_bypass: [],
          used_today: 8,
          status: "active",
          last_reset_at: new Date(timestamp).getTime() / 1000 - 6 * 60 * 60,
          metadata: {},
          created_at: new Date(timestamp).getTime() / 1000 - 30 * 24 * 60 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 60 * 60,
        },
        {
          id: "home-agent",
          scope_type: "agent",
          scope_id: "home-agent",
          daily_limit: 12,
          urgent_bypass: ["security_alert", "security_action_requested"],
          used_today: 3,
          status: "active",
          last_reset_at: new Date(timestamp).getTime() / 1000 - 6 * 60 * 60,
          metadata: {},
          created_at: new Date(timestamp).getTime() / 1000 - 30 * 24 * 60 * 60,
          updated_at: new Date(timestamp).getTime() / 1000 - 60 * 60,
        },
      ];
      return {
        budgets,
        count: budgets.length,
        attention_posture: {
          open_inbox_count: 11,
          urgent_inbox_count: 4,
          pending_approval_count: 1,
          blocked_run_count: 3,
          stale_blocked_run_count: 3,
          recommended_mode: "constrained",
          breaches: [
            "attention:open_inbox",
            "attention:urgent_inbox",
            "attention:stale_blocked_runs",
          ],
          by_status: {
            new: 1,
            acknowledged: 1,
            snoozed: 1,
          },
        },
      };
    }

  const projectPacketMatch = basePath.match(/^\/v1\/projects\/([^/]+)\/packet$/);
  if (projectPacketMatch) {
    const projectId = decodeURIComponent(projectPacketMatch[1] ?? "");
    if (method === "GET") {
      return { packet: buildFixtureProjectPacket(projectId) };
    }
    if (method === "POST") {
      return {
        status: "updated",
        packet: {
          ...buildFixtureProjectPacket(projectId),
          ...(payload ?? {}),
          id: projectId,
          updated_at: new Date(timestamp).getTime() / 1000,
        },
      };
    }
  }

  const architectureMatch = basePath.match(/^\/v1\/projects\/([^/]+)\/architecture$/);
  if (architectureMatch) {
    const projectId = decodeURIComponent(architectureMatch[1] ?? "");
    if (method === "GET") {
      return { architecture: buildFixtureArchitecturePacket(projectId) };
    }
    if (method === "POST") {
      return {
        status: "updated",
        architecture: {
          ...buildFixtureArchitecturePacket(projectId),
          ...(payload ?? {}),
          project_id: projectId,
          updated_at: new Date(timestamp).getTime() / 1000,
        },
      };
    }
  }

  const foundryRunsMatch = basePath.match(/^\/v1\/projects\/([^/]+)\/foundry\/runs$/);
  if (foundryRunsMatch) {
    const projectId = decodeURIComponent(foundryRunsMatch[1] ?? "");
    if (method === "GET") {
      const runs = buildFixtureFoundryRuns(projectId).slice(0, limit ?? undefined);
      return { runs, count: runs.length };
    }
    if (method === "POST") {
      return {
        status: "created",
        run: {
          ...buildFixtureFoundryRuns(projectId)[0],
          ...(payload ?? {}),
          id:
            typeof payload?.id === "string" && payload.id.length > 0
              ? payload.id
              : `${projectId}-foundry-run-new`,
          project_id: projectId,
          created_at: new Date(timestamp).getTime() / 1000,
          updated_at: new Date(timestamp).getTime() / 1000,
        },
      };
    }
  }

  const slicesMatch = basePath.match(/^\/v1\/projects\/([^/]+)\/slices$/);
  if (slicesMatch) {
    const projectId = decodeURIComponent(slicesMatch[1] ?? "");
    if (method === "GET") {
      const slices = buildFixtureExecutionSlices(projectId).slice(0, limit ?? undefined);
      return { slices, count: slices.length };
    }
    if (method === "POST") {
      return {
        status: "created",
        slice: {
          ...buildFixtureExecutionSlices(projectId)[0],
          ...(payload ?? {}),
          id:
            typeof payload?.id === "string" && payload.id.length > 0
              ? payload.id
              : `${projectId}-slice-new`,
          project_id: projectId,
          created_at: new Date(timestamp).getTime() / 1000,
          updated_at: new Date(timestamp).getTime() / 1000,
        },
      };
    }
  }

  const deploymentsMatch = basePath.match(/^\/v1\/projects\/([^/]+)\/deployments$/);
  if (deploymentsMatch) {
    const projectId = decodeURIComponent(deploymentsMatch[1] ?? "");
    if (method === "GET") {
      const deployments = buildFixtureDeployments(projectId).slice(0, limit ?? undefined);
      return { deployments, count: deployments.length };
    }
    if (method === "POST") {
      return {
        status: "created",
        deployment: {
          ...buildFixtureDeployments(projectId)[0],
          ...(payload ?? {}),
          id:
            typeof payload?.id === "string" && payload.id.length > 0
              ? payload.id
              : `${projectId}-candidate-new`,
          project_id: projectId,
          created_at: new Date(timestamp).getTime() / 1000,
          updated_at: new Date(timestamp).getTime() / 1000,
        },
      };
    }
  }

  const maintenanceMatch = basePath.match(/^\/v1\/projects\/([^/]+)\/maintenance$/);
  if (maintenanceMatch) {
    const projectId = decodeURIComponent(maintenanceMatch[1] ?? "");
    if (method === "GET") {
      const maintenance_runs = buildFixtureMaintenanceRuns(projectId).slice(0, limit ?? undefined);
      return { maintenance_runs, count: maintenance_runs.length };
    }
    if (method === "POST") {
      return {
        status: "created",
        maintenance_run: {
          ...buildFixtureMaintenanceRuns(projectId)[0],
          ...(payload ?? {}),
          id:
            typeof payload?.id === "string" && payload.id.length > 0
              ? payload.id
              : `${projectId}-maintenance-new`,
          project_id: projectId,
          created_at: new Date(timestamp).getTime() / 1000,
          updated_at: new Date(timestamp).getTime() / 1000,
        },
      };
    }
  }

  const rollbacksMatch = basePath.match(/^\/v1\/projects\/([^/]+)\/rollbacks$/);
  if (rollbacksMatch && method === "GET") {
    const projectId = decodeURIComponent(rollbacksMatch[1] ?? "");
    const rollbacks = buildFixtureRollbacks(projectId).slice(0, limit ?? undefined);
    return { rollbacks, count: rollbacks.length };
  }

  const promoteMatch = basePath.match(/^\/v1\/projects\/([^/]+)\/promote$/);
  if (promoteMatch && method === "POST") {
    const projectId = decodeURIComponent(promoteMatch[1] ?? "");
    const candidateId =
      typeof payload?.candidate_id === "string" && payload.candidate_id.length > 0
        ? payload.candidate_id
        : `${projectId}-candidate-1`;
    const channel =
      typeof payload?.channel === "string" && payload.channel.length > 0
        ? payload.channel
        : "internal_preview";
    return {
      status: "promoted",
      candidate: {
        ...buildFixtureDeployments(projectId)[0],
        id: candidateId,
        project_id: projectId,
        channel,
        promotion_status: "promoted",
        metadata: {
          source: "dashboard_fixture",
          promotion_reason:
            typeof payload?.reason === "string" ? payload.reason : "Fixture promotion",
        },
        promoted_at: new Date(timestamp).getTime() / 1000,
        updated_at: new Date(timestamp).getTime() / 1000,
      },
    };
  }

  const rollbackMatch = basePath.match(/^\/v1\/projects\/([^/]+)\/rollback$/);
  if (rollbackMatch && method === "POST") {
    const projectId = decodeURIComponent(rollbackMatch[1] ?? "");
    const candidateId =
      typeof payload?.candidate_id === "string" && payload.candidate_id.length > 0
        ? payload.candidate_id
        : `${projectId}-candidate-0`;
    return {
      status: "rolled_back",
      candidate: {
        ...buildFixtureDeployments(projectId)[1],
        id: candidateId,
        project_id: projectId,
        promotion_status: "rolled_back",
        metadata: {
          source: "dashboard_fixture",
          rollback_reason:
            typeof payload?.reason === "string" ? payload.reason : "Fixture rollback",
        },
        updated_at: new Date(timestamp).getTime() / 1000,
      },
      rollback_event: {
        id: `${projectId}-rollback-new`,
        project_id: projectId,
        candidate_id: candidateId,
        reason:
          typeof payload?.reason === "string" ? payload.reason : "Fixture rollback",
        rollback_target: buildFixtureDeployments(projectId)[1].rollback_target,
        status: "executed",
        metadata: {
          channel: buildFixtureDeployments(projectId)[1].channel,
          source: "dashboard_fixture",
        },
        created_at: new Date(timestamp).getTime() / 1000,
      },
    };
  }

  const fixtureBootstrapTakeover = {
    ready: false,
    blocker_ids: [
      "durable_persistence_live",
      "governance_drills_green",
      "external_dependency_removed",
    ],
    criteria: [
      {
        id: "software_core_active",
        label: "Software-core autonomy active",
        passed: true,
        detail:
          "Current autonomy phase is full_system_phase_3 and active, which keeps software-core autonomy live.",
      },
      {
        id: "canonical_operator_work_system",
        label: "Canonical operator work system",
        passed: true,
        detail: "Canonical operator work surfaces are live.",
      },
      {
        id: "compatibility_retirement_complete",
        label: "Compatibility retirement complete",
        passed: true,
        detail: "Compatibility retirement is closed from census and contract evidence.",
      },
      {
        id: "durable_persistence_live",
        label: "Durable persistence live",
        passed: false,
        detail: "Schema/runtime cutover and restart proof remain approval-gated.",
      },
      {
        id: "foundry_path_live",
        label: "Foundry path live",
        passed: true,
        detail: "Foundry proving packet has project, architecture, slice, run, candidate, and rollback evidence.",
      },
      {
        id: "governance_drills_green",
        label: "Governance drills green",
        passed: false,
        detail: "Governance drill evidence is still failing: constrained-mode, degraded-mode, and recovery-only all require durable persistence.",
      },
      {
        id: "external_dependency_removed",
        label: "External-host-only dependency removed",
        passed: false,
        detail: "External builders are still primary in the bootstrap posture.",
      },
    ],
  };
  const fixtureBootstrapProgram = {
    id: "launch-readiness-bootstrap",
    label: "Launch readiness bootstrap",
    objective:
      "Use the external recursive builder stack to finish the Athanor builder stack until explicit takeover is justified.",
    phase_scope: "software_core_phase_1",
    status: "waiting_approval",
    current_family: "durable_persistence_activation",
    next_slice_id: "",
    recommended_host_id: "",
    waiting_on_approval_family: "durable_persistence_activation",
    waiting_on_approval_slice_id: "persist-04-activation-cutover",
    next_action: {
      kind: "approval_required",
      family: "durable_persistence_activation",
      slice_id: "persist-04-activation-cutover",
      approval_class: "approval_packet",
      blocking_packet_id: "approval_packet",
      open_blocker_ids: ["blocker-40429ccbc0"],
    },
    pending_integrations: 0,
    slice_counts: {
      total: 30,
      queued: 2,
      active: 0,
      blocked: 0,
      completed: 28,
    },
  };
  const fixtureBootstrapSlices = [
    {
      id: "compat-04-completion-detector",
      program_id: "launch-readiness-bootstrap",
      family: "compatibility_retirement",
      objective: "Keep first-class workforce compatibility retirement enforced by contract.",
      status: "completed",
      host_id: "codex_external",
      validation_status: "passed",
      next_step: "Compatibility retirement is closed.",
    },
    {
      id: "persist-03-runtime-dependency-packet",
      program_id: "launch-readiness-bootstrap",
      family: "durable_persistence_activation",
      objective: "Freeze the durable runtime dependency and env contract.",
      status: "completed",
      host_id: "codex_external",
      validation_status: "passed",
      next_step: "Wait for approval to cut configured runtimes over to durable persistence.",
    },
    {
      id: "persist-04-activation-cutover",
      program_id: "launch-readiness-bootstrap",
      family: "durable_persistence_activation",
      objective: "Cut configured Postgres runtimes over from fallback memory to durable persistence.",
      status: "waiting_approval",
      host_id: "",
      validation_status: "pending",
      next_step: "Await DB schema/runtime approval packet execution.",
    },
    {
      id: "persist-05-restart-proof",
      program_id: "launch-readiness-bootstrap",
      family: "durable_persistence_activation",
      objective: "Capture restart-safe durable recovery evidence after cutover.",
      status: "waiting_approval",
      host_id: "",
      validation_status: "pending",
      next_step: "Run after durable cutover lands.",
    },
    {
      id: "opsurf-03-fixture-parity",
      program_id: "launch-readiness-bootstrap",
      family: "operator_surface_canonicalization",
      objective: "Keep fixture mode coherent for every canonical operator and bootstrap route.",
      status: "completed",
      host_id: "codex_external",
      validation_status: "passed",
      next_step: "Fixture parity is locked to canonical operator and bootstrap routes.",
    },
    {
      id: "opsurf-04-nav-lock",
      program_id: "launch-readiness-bootstrap",
      family: "operator_surface_canonicalization",
      objective: "Freeze navigation truth so compatibility pages are explicit redirects only.",
      status: "completed",
      host_id: "codex_external",
      validation_status: "passed",
      next_step: "Navigation truth is locked to canonical operator surfaces with explicit compatibility redirects.",
    },
    {
      id: "opsurf-05-surface-contract",
      program_id: "launch-readiness-bootstrap",
      family: "operator_surface_canonicalization",
      objective: "Add contract coverage that fails if first-class surfaces consume non-canonical operator data.",
      status: "queued",
      host_id: "",
      validation_status: "pending",
      next_step: "Run the surface contract bundle and keep operator nav lock green.",
    },
  ];
  const fixtureBootstrapHandoffs = [
    {
      id: "handoff-opsurf-02-fixture",
      slice_id: "opsurf-02-summary-alignment",
      from_host: "claude_external",
      to_host: "codex_external",
      stop_reason: "context_exhausted",
      next_step: "Finish aligning first-class digest and shell summary surfaces on canonical operator summary data.",
      resume_instructions: "Resume from the existing operator surface lane without restarting the slice.",
    },
  ];
  const fixtureBootstrapBlockers = [
    {
      id: "blocker-40429ccbc0",
      family: "durable_persistence_activation",
      blocker_class: "approval_required",
      reason: "Slice persist-04-activation-cutover requires explicit operator approval before runtime mutation or promotion-sensitive continuation.",
      approval_required: true,
      inbox_id: "inbox-f58560ce",
    },
    {
      id: "blocker-5efe04adf2",
      family: "durable_persistence_activation",
      blocker_class: "approval_required",
      reason: "Slice persist-05-restart-proof requires explicit operator approval before runtime mutation or promotion-sensitive continuation.",
      approval_required: true,
      inbox_id: "inbox-79a19f3e",
    },
    {
      id: "blocker-02183d3fb6",
      family: "governance_rehearsal",
      blocker_class: "governance_drill_failed",
      reason: "Governance drill constrained-mode is not green: durable system-mode persistence is unavailable because ATHANOR_POSTGRES_URL is not configured.",
      approval_required: false,
      inbox_id: "",
    },
    {
      id: "blocker-d11400e7b2",
      family: "governance_rehearsal",
      blocker_class: "governance_drill_failed",
      reason: "Governance drill degraded-mode is not green: durable system-mode persistence is unavailable because ATHANOR_POSTGRES_URL is not configured.",
      approval_required: false,
      inbox_id: "",
    },
    {
      id: "blocker-93e86901b0",
      family: "governance_rehearsal",
      blocker_class: "governance_drill_failed",
      reason: "Governance drill recovery-only is not green: durable system-mode persistence is unavailable because ATHANOR_POSTGRES_URL is not configured.",
      approval_required: false,
      inbox_id: "",
    },
  ];
  const fixtureBootstrapIntegrations: Array<Record<string, unknown>> = [];
  const fixtureBootstrapStatus = {
    mode: "ready",
    authority: "hybrid_local_ledger",
    sqlite_ready: true,
    mirror_ready: false,
    mirror_configured: false,
    program_count: 1,
    slice_count: 37,
    open_blockers: fixtureBootstrapBlockers.length,
    busy_hosts: 0,
    pending_integrations: fixtureBootstrapIntegrations.length,
    active_program_id: fixtureBootstrapProgram.id,
    active_family: fixtureBootstrapProgram.current_family,
    next_slice_id: fixtureBootstrapProgram.next_slice_id,
    recommended_host_id: fixtureBootstrapProgram.recommended_host_id,
    waiting_on_approval_family: fixtureBootstrapProgram.waiting_on_approval_family,
    waiting_on_approval_slice_id: fixtureBootstrapProgram.waiting_on_approval_slice_id,
    next_action: fixtureBootstrapProgram.next_action,
    approval_context: {
      kind: "approval_required",
      family: "durable_persistence_activation",
      slice_id: "persist-04-activation-cutover",
      approval_class: "approval_packet",
      packet_id: "db_schema_change",
      packet_label: "DB schema change",
      approval_authority: "operator",
      open_blocker_ids: ["blocker-40429ccbc0"],
      follow_on_slice_id: "persist-05-restart-proof",
      summary: "Authorize the durable persistence schema and runtime cutover maintenance window.",
      unlocks:
        "Unblocks persist-04-activation-cutover and the follow-on persist-05-restart-proof restart-proof slice.",
      operator_instruction:
        "Approve db_schema_change for persist-04-activation-cutover and proceed with the maintenance window. After cutover, continue with persist-05-restart-proof.",
      review_artifacts: [
        "C:\\Athanor\\reports\\bootstrap\\durable-persistence-packet.json",
        "C:\\Athanor\\config\\automation-backbone\\approval-packet-registry.json",
        "C:\\Athanor\\projects\\agents\\src\\athanor_agents\\sql\\bootstrap_durable_state.sql",
        "C:\\Athanor\\reports\\bootstrap\\latest.json",
      ],
      exact_steps: [
        "Create checkpoint tables or mirrored bootstrap/run tables in implementation authority SQL first.",
        "Review dependency and env changes before runtime mutation.",
        "Apply schema change during an intentional maintenance window only.",
        "Run restart-safe recovery proof before clearing the durable-persistence blocker.",
      ],
      rollback_steps: [
        "Stop the runtime mutation path.",
        "Restore pre-migration schema snapshot or backup.",
        "Return runtime to the previous persistence posture.",
      ],
    },
    control_artifacts: {
      snapshot_path: "C:\\Athanor\\reports\\bootstrap\\latest.json",
      durable_persistence_packet_path: "C:\\Athanor\\reports\\bootstrap\\durable-persistence-packet.json",
      approval_packet_registry_path: "C:\\Athanor\\config\\automation-backbone\\approval-packet-registry.json",
      durable_state_sql_path: "C:\\Athanor\\projects\\agents\\src\\athanor_agents\\sql\\bootstrap_durable_state.sql",
    },
    hosts: [
      {
        id: "codex_external",
        status: "available",
        active_slice_id: "",
        last_reason: "Awaiting explicit durable-persistence approval.",
      },
      {
        id: "claude_external",
        status: "available",
        active_slice_id: "",
        last_reason: "Standing by for automatic relay.",
      },
    ],
    takeover: fixtureBootstrapTakeover,
  };
  const fixtureBootstrapNextSlice =
    fixtureBootstrapSlices.find((slice) => slice.id === fixtureBootstrapProgram.next_slice_id) ?? null;
  const fixtureApprovedBootstrapProgram = {
    ...fixtureBootstrapProgram,
    status: "active",
    current_family: "durable_persistence_activation",
    next_slice_id: "persist-04-activation-cutover",
    recommended_host_id: "codex_external",
    waiting_on_approval_family: "",
    waiting_on_approval_slice_id: "",
    next_action: {
      kind: "dispatch",
      family: "durable_persistence_activation",
      slice_id: "persist-04-activation-cutover",
      host_id: "codex_external",
      worktree_required: true,
    },
  };
  const fixtureApprovedBootstrapStatus = {
    ...fixtureBootstrapStatus,
    active_family: fixtureApprovedBootstrapProgram.current_family,
    next_slice_id: fixtureApprovedBootstrapProgram.next_slice_id,
    recommended_host_id: fixtureApprovedBootstrapProgram.recommended_host_id,
    waiting_on_approval_family: "",
    waiting_on_approval_slice_id: "",
    next_action: fixtureApprovedBootstrapProgram.next_action,
    approval_context: null,
    open_blockers: fixtureBootstrapBlockers.filter((blocker) => !String(blocker.id).startsWith("blocker-40429") && !String(blocker.id).startsWith("blocker-5efe04")).length,
    hosts: [
      {
        id: "codex_external",
        status: "available",
        active_slice_id: "",
        last_reason: "Approval recorded; durable cutover is dispatchable.",
      },
      {
        id: "claude_external",
        status: "available",
        active_slice_id: "",
        last_reason: "Standing by for automatic relay.",
      },
    ],
  };

  if (method === "GET" && basePath === "/v1/bootstrap/programs") {
    return {
      programs: [fixtureBootstrapProgram],
      count: 1,
      status: fixtureBootstrapStatus,
      takeover: fixtureBootstrapTakeover,
    };
  }

  if (method === "GET" && /^\/v1\/bootstrap\/programs\/[^/]+$/.test(basePath)) {
    return {
      program: fixtureBootstrapProgram,
      status: fixtureBootstrapStatus,
      takeover: fixtureBootstrapTakeover,
      next_slice: fixtureBootstrapNextSlice,
    };
  }

  if (method === "GET" && basePath === "/v1/bootstrap/slices") {
    return { slices: fixtureBootstrapSlices, count: fixtureBootstrapSlices.length };
  }

  if (method === "GET" && basePath === "/v1/bootstrap/handoffs") {
    return { handoffs: fixtureBootstrapHandoffs, count: fixtureBootstrapHandoffs.length };
  }

  if (method === "GET" && basePath === "/v1/bootstrap/blockers") {
    return { blockers: fixtureBootstrapBlockers, count: fixtureBootstrapBlockers.length };
  }

  if (method === "GET" && basePath === "/v1/bootstrap/integrations") {
    return { integrations: fixtureBootstrapIntegrations, count: fixtureBootstrapIntegrations.length };
  }

  if (method === "POST" && /^\/v1\/bootstrap\/programs\/[^/]+\/nudge$/.test(basePath)) {
    return {
      status: "nudged",
      active_program_id: fixtureBootstrapProgram.id,
      active_family: fixtureBootstrapProgram.current_family,
      recommendation: {
        slice_id: fixtureBootstrapProgram.next_slice_id,
        host_id: fixtureBootstrapProgram.recommended_host_id,
        ready: false,
      },
      next_action: fixtureBootstrapProgram.next_action,
    };
  }

  const bootstrapApproveMatch = basePath.match(/^\/v1\/bootstrap\/programs\/([^/]+)\/approve$/);
  if (method === "POST" && bootstrapApproveMatch) {
    const programId = decodeURIComponent(bootstrapApproveMatch[1] ?? "");
    const packetId = typeof payload?.packet_id === "string" && payload.packet_id.length > 0 ? payload.packet_id : "db_schema_change";
    return {
      status: "approved",
      approved_packet_id: packetId,
      approved_slice_ids: ["persist-04-activation-cutover", "persist-05-restart-proof"],
      resolved_blocker_ids: ["blocker-40429ccbc0", "blocker-5efe04adf2"],
      program: {
        ...fixtureApprovedBootstrapProgram,
        id: programId || fixtureApprovedBootstrapProgram.id,
      },
      snapshot: fixtureApprovedBootstrapStatus,
      takeover: fixtureBootstrapTakeover,
      recommendation: {
        slice_id: "persist-04-activation-cutover",
        host_id: "codex_external",
        ready: true,
      },
      next_action: fixtureApprovedBootstrapProgram.next_action,
      timestamp,
    };
  }

  if (method === "POST" && /^\/v1\/bootstrap\/programs\/[^/]+\/promote$/.test(basePath)) {
    return {
      status: "promoted",
      program: {
        ...fixtureBootstrapProgram,
        status: "takeover_promoted",
        metadata: {
          internal_builder_primary: true,
          promoted_at: timestamp,
          promoted_by: "operator",
        },
      },
    };
  }

  const bootstrapClaimMatch = basePath.match(/^\/v1\/bootstrap\/slices\/([^/]+)\/claim$/);
  if (method === "POST" && bootstrapClaimMatch) {
    const sliceId = decodeURIComponent(bootstrapClaimMatch[1] ?? "");
    const current = fixtureBootstrapSlices.find((slice) => slice.id === sliceId);
    return {
      status: "claimed",
      slice: {
        ...(current ?? {
          id: sliceId,
          program_id: fixtureBootstrapProgram.id,
          family: fixtureBootstrapProgram.current_family,
          objective: "Fixture bootstrap slice claim",
        }),
        status: "claimed",
        host_id: typeof payload?.host_id === "string" ? payload.host_id : "codex_external",
        current_ref: typeof payload?.current_ref === "string" ? payload.current_ref : "HEAD",
        worktree_path:
          typeof payload?.worktree_path === "string" && payload.worktree_path.length > 0
            ? payload.worktree_path
            : `C:\\Athanor_worktrees\\${current?.family ?? fixtureBootstrapProgram.current_family}\\${sliceId}`,
        files_touched: Array.isArray(payload?.files_touched) ? payload.files_touched : [],
        next_step:
          typeof payload?.next_step === "string" && payload.next_step.length > 0
            ? payload.next_step
            : current?.next_step ?? "",
        claimed_at: new Date(timestamp).getTime() / 1000,
      },
      timestamp,
    };
  }

  const bootstrapCompleteMatch = basePath.match(/^\/v1\/bootstrap\/slices\/([^/]+)\/complete$/);
  if (method === "POST" && bootstrapCompleteMatch) {
    const sliceId = decodeURIComponent(bootstrapCompleteMatch[1] ?? "");
    const current = fixtureBootstrapSlices.find((slice) => slice.id === sliceId);
    const validationStatus =
      typeof payload?.validation_status === "string" ? payload.validation_status : "passed";
    return {
      status: "completed",
      slice: {
        ...(current ?? {
          id: sliceId,
          program_id: fixtureBootstrapProgram.id,
          family: fixtureBootstrapProgram.current_family,
          objective: "Fixture bootstrap slice completion",
        }),
        status: "completed",
        host_id: typeof payload?.host_id === "string" ? payload.host_id : "codex_external",
        validation_status: validationStatus,
        next_step: typeof payload?.next_step === "string" ? payload.next_step : "",
        summary: typeof payload?.summary === "string" ? payload.summary : "",
        completed_at: new Date(timestamp).getTime() / 1000,
      },
      integration:
        validationStatus === "passed"
          ? {
              id: `integration-${sliceId}`,
              slice_id: sliceId,
              family: current?.family ?? fixtureBootstrapProgram.current_family,
              method:
                typeof payload?.integration_method === "string" ? payload.integration_method : "squash_commit",
              target_ref: typeof payload?.target_ref === "string" ? payload.target_ref : "main",
              status: "queued",
              priority: typeof payload?.queue_priority === "number" ? payload.queue_priority : 3,
            }
          : null,
      timestamp,
    };
  }

  const bootstrapHandoffMatch = basePath.match(/^\/v1\/bootstrap\/slices\/([^/]+)\/handoff$/);
  if (method === "POST" && bootstrapHandoffMatch) {
    const sliceId = decodeURIComponent(bootstrapHandoffMatch[1] ?? "");
    return {
      status: "handed_off",
      handoff: {
        id: `handoff-${sliceId}`,
        slice_id: sliceId,
        from_host: typeof payload?.from_host === "string" ? payload.from_host : "codex_external",
        to_host: typeof payload?.to_host === "string" ? payload.to_host : "claude_external",
        current_ref: typeof payload?.current_ref === "string" ? payload.current_ref : "HEAD",
        worktree_path:
          typeof payload?.worktree_path === "string" && payload.worktree_path.length > 0
            ? payload.worktree_path
            : `C:\\Athanor_worktrees\\${fixtureBootstrapProgram.current_family}\\${sliceId}`,
        files_touched: Array.isArray(payload?.files_touched) ? payload.files_touched : [],
        validation_status: typeof payload?.validation_status === "string" ? payload.validation_status : "pending",
        open_risks: Array.isArray(payload?.open_risks) ? payload.open_risks : [],
        next_step: typeof payload?.next_step === "string" ? payload.next_step : "",
        stop_reason: typeof payload?.stop_reason === "string" ? payload.stop_reason : "",
        resume_instructions: typeof payload?.resume_instructions === "string" ? payload.resume_instructions : "",
        cooldown_minutes: typeof payload?.cooldown_minutes === "number" ? payload.cooldown_minutes : 30,
        created_at: new Date(timestamp).getTime() / 1000,
      },
      timestamp,
    };
  }

  const bootstrapReplayMatch = basePath.match(/^\/v1\/bootstrap\/integrations\/([^/]+)\/replay$/);
  if (method === "POST" && bootstrapReplayMatch) {
    const sliceId = decodeURIComponent(bootstrapReplayMatch[1] ?? "");
    const current = fixtureBootstrapSlices.find((slice) => slice.id === sliceId);
    return {
      status: "queued",
      integration: {
        id: `integration-${sliceId}`,
        slice_id: sliceId,
        family: current?.family ?? fixtureBootstrapProgram.current_family,
        method: typeof payload?.method === "string" ? payload.method : "squash_commit",
        source_ref: typeof payload?.source_ref === "string" ? payload.source_ref : "",
        target_ref: typeof payload?.target_ref === "string" ? payload.target_ref : "main",
        patch_path: typeof payload?.patch_path === "string" ? payload.patch_path : "",
        status: "queued",
        priority: typeof payload?.priority === "number" ? payload.priority : 3,
      },
      timestamp,
    };
  }

  if (method === "GET" && basePath === "/v1/operator/summary") {
      const patternReport = getFixtureAgentPatterns({});
      const patternItems = Array.isArray(patternReport?.patterns)
        ? (patternReport.patterns.filter(
            (item) =>
              typeof item === "object" &&
              item !== null &&
              ["high", "medium"].includes(String((item as Record<string, unknown>)["severity"] ?? ""))
          ) as Array<Record<string, unknown>>)
        : [];
      const outputPreview = getFixtureAgentOutputs().slice(0, 5);
      return {
        ideas: {
          total: 3,
          by_status: {
            candidate: 1,
            sprout: 1,
            seed: 1,
          },
        },
        inbox: {
          total: 3,
          by_status: {
            new: 1,
            acknowledged: 1,
            snoozed: 1,
            resolved: 0,
            converted: 0,
          },
        },
        todos: {
          total: 3,
          by_status: {
            open: 1,
            ready: 1,
            blocked: 0,
            waiting: 0,
            done: 0,
            cancelled: 0,
            someday: 1,
          },
        },
        backlog: {
          total: 3,
          by_status: {
            ready: 1,
            blocked: 1,
            waiting_approval: 1,
          },
        },
        runs: {
          total: 3,
          by_status: {
            running: 1,
            waiting_approval: 1,
            completed: 1,
          },
        },
        approvals: {
          total: 1,
          by_status: {
            pending: 1,
          },
        },
        tasks: {
          total: 7,
          by_status: {
            completed: 4,
            failed: 2,
            pending_approval: 1,
            stale_lease: 1,
          },
          pending_approval: 1,
          stale_lease: 1,
          failed_actionable: 1,
          failed_historical_repaired: 1,
          failed_missing_detail: 0,
        },
        digest: {
          type: "auto",
          generated_at: timestamp,
          period: "24h",
          summary: "4 tasks completed, 1 failed in the last 24 hours. Canonical operator work stayed active overnight.",
          task_count: 5,
          completed_count: 4,
          failed_count: 1,
          recent_completions: [
            {
              id: "run-ath-1",
              title: "Refresh command-center route taxonomy",
              result_preview: "Canonical operator and bootstrap routes are aligned across the shell.",
            },
            {
              id: "run-ath-2",
              title: "Queue zero-ambiguity proving packet",
              result_preview: "Foundry packet evidence is staged and waiting on the next execution slice.",
            },
          ],
          recent_failures: [
            {
              id: "run-ath-fail-1",
              title: "Durable persistence cutover",
              error: "Schema/runtime mutation is still approval-gated.",
            },
          ],
        },
        projects: {
          stalled_total: 1,
          stalled_preview: [
            {
              id: "athanor",
              name: "Athanor",
              reason: "No milestone activity for more than 24 hours.",
              stalled_since: isoMinutesBefore(180),
            },
          ],
          threshold_hours: 24,
        },
        outputs: {
          total: outputPreview.length,
          recent: outputPreview,
        },
        patterns: {
          available: true,
          generated_at: timestamp,
          warning_count: patternItems.length,
          high_count: patternItems.filter((item) => String(item["severity"] ?? "") === "high").length,
          medium_count: patternItems.filter((item) => String(item["severity"] ?? "") === "medium").length,
          patterns: patternItems.slice(0, 5),
          recommendations: Array.isArray(patternReport?.recommendations)
            ? patternReport.recommendations.slice(0, 3)
            : [],
        },
        bootstrap: {
          mode: "ready",
          sqlite_ready: true,
          mirror_ready: false,
          program_count: 1,
          slice_count: 7,
          open_blockers: 1,
          busy_hosts: 1,
          hosts: [
            { id: "codex_external", status: "busy", active_slice_id: "slice-compatibility-retirement", last_reason: "Claimed slice" },
            { id: "claude_external", status: "available", active_slice_id: "", last_reason: "Waiting for relay" },
          ],
          takeover: {
            ready: false,
            blocker_ids: [
              "compatibility_retirement_complete",
              "durable_persistence_live",
              "governance_drills_green",
              "external_dependency_removed",
            ],
            criteria: [],
          },
        },
        governance: {
          current_mode: {
            id: "mode-constrained-fixture",
            mode: "constrained",
            entered_at: new Date(timestamp).getTime() / 1000 - 45 * 60,
            entered_by: "operator",
            trigger: "attention_breach",
            exit_conditions: "Clear attention breaches for 15 minutes.",
            notes: "Fixture governance posture while the launch-readiness tranche is in flight.",
            metadata: {},
          },
          launch_ready: true,
          launch_blockers: [],
          issues: [
            "attention:open_inbox",
            "attention:urgent_inbox",
            "attention:stale_blocked_runs",
          ],
          attention_posture: {
            open_inbox_count: 11,
            urgent_inbox_count: 4,
            pending_approval_count: 1,
            blocked_run_count: 3,
            stale_blocked_run_count: 3,
            recommended_mode: "constrained",
            breaches: [
              "attention:open_inbox",
              "attention:urgent_inbox",
              "attention:stale_blocked_runs",
            ],
            by_status: {
              new: 1,
              acknowledged: 1,
              snoozed: 1,
            },
          },
        },
      };
    }

  if (method === "GET" && basePath === "/v1/activity") {
    const activity = getFixtureAgentActivity({ agent, limit });
    return {
      activity,
      count: activity.length,
    };
  }

  if (method === "GET" && basePath === "/v1/activity/stats") {
    return {
      stats: buildFixtureActivityStats(agent),
    };
  }

  if (method === "GET" && basePath === "/v1/improvement/summary") {
    return buildFixtureImprovementSummary(timestamp);
  }

  if (method === "GET" && basePath === "/v1/improvement/proposals") {
    return {
      proposals: buildFixtureImprovementProposals(),
      count: buildFixtureImprovementProposals().length,
    };
  }

  if (method === "GET" && basePath === "/v1/improvement/benchmarks/history") {
    const entries = buildFixtureBenchmarkHistory(timestamp);
    return {
      entries,
      count: entries.length,
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
        { id: "anthropic_claude_code", name: "Claude Code", default_task_class: "repo_wide_audit" },
        { id: "openai_codex", name: "OpenAI Codex", default_task_class: "async_backlog_execution" },
        { id: "google_gemini", name: "Gemini CLI", default_task_class: "repo_wide_audit" },
        { id: "moonshot_kimi", name: "Kimi Code", default_task_class: "search_heavy_planning" },
        { id: "zai_glm_coding", name: "Z.ai GLM Coding", default_task_class: "cheap_bulk_transform" },
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
      providers: ["anthropic_claude_code", "openai_codex", "google_gemini", "moonshot_kimi", "zai_glm_coding"],
      task_classes: {
        async_backlog_execution: { primary: "openai_codex" },
        repo_wide_audit: { primary: "google_gemini" },
        search_heavy_planning: { primary: "moonshot_kimi" },
        multi_file_implementation: { primary: "anthropic_claude_code" },
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
          provider: "anthropic_claude_code",
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
        provider: "anthropic_claude_code",
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
        anthropic_claude_code: { status: "available", remaining: 18, limit: 25 },
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

  if (method === "GET" && basePath === "/v1/subscriptions/provider-status") {
    return {
      providers: [
        {
          id: "athanor_local",
          name: "Athanor Local",
          subscription: "Sovereign local cluster",
          monthly_cost: 0,
          pricing_status: "not_applicable",
          role: "default_local_execution",
          category: "local",
          status: "available",
          provider_state: "available",
          state_reasons: ["direct_or_local_path_ready"],
          execution_mode: "local_runtime",
          direct_execution_ready: true,
          governed_handoff_ready: false,
          available: true,
          tasks_today: 14,
          quota_remaining: null,
          last_used: "2026-03-11T18:58:00Z",
          avg_latency_ms: null,
        },
        {
          id: "anthropic_claude_code",
          name: "Claude Code",
          subscription: "Claude Max",
          monthly_cost: 200,
          pricing_status: "official_verified",
          role: "frontier_supervisor",
          category: "subscription",
          status: "available",
          provider_state: "available",
          state_reasons: ["direct_or_local_path_ready"],
          execution_mode: "direct_cli",
          direct_execution_ready: true,
          governed_handoff_ready: true,
          available: true,
          tasks_today: 9,
          quota_remaining: null,
          last_used: "2026-03-11T18:47:00Z",
          avg_latency_ms: 1800,
        },
        {
          id: "google_gemini",
          name: "Gemini CLI",
          subscription: "Google AI Pro / Gemini CLI",
          monthly_cost: 20,
          pricing_status: "official_verified",
          role: "repo_audit_supervisor",
          category: "subscription",
          status: "available",
          provider_state: "available",
          state_reasons: ["direct_or_local_path_ready"],
          execution_mode: "handoff_bundle",
          direct_execution_ready: false,
          governed_handoff_ready: true,
          available: true,
          tasks_today: 6,
          quota_remaining: 23,
          last_used: "2026-03-11T17:33:00Z",
          avg_latency_ms: 2400,
        },
        {
          id: "moonshot_kimi",
          name: "Kimi Code",
          subscription: "Kimi Membership / Kimi Code",
          monthly_cost: null,
          pricing_status: "official-source-present-cost-unverified",
          role: "search_heavy_planning",
          category: "subscription",
          status: "available",
          provider_state: "available",
          state_reasons: ["direct_or_local_path_ready"],
          execution_mode: "direct_cli",
          direct_execution_ready: true,
          governed_handoff_ready: true,
          available: true,
          tasks_today: 3,
          quota_remaining: null,
          last_used: "2026-03-11T16:10:00Z",
          avg_latency_ms: 2100,
        },
        {
          id: "openai_codex",
          name: "OpenAI Codex",
          subscription: "ChatGPT Pro",
          monthly_cost: 200,
          pricing_status: "official_verified",
          role: "async_backlog_execution",
          category: "subscription",
          status: "available",
          provider_state: "available",
          state_reasons: ["direct_or_local_path_ready"],
          execution_mode: "direct_cli",
          direct_execution_ready: true,
          governed_handoff_ready: true,
          available: true,
          tasks_today: 4,
          quota_remaining: null,
          last_used: "2026-03-11T18:02:00Z",
          avg_latency_ms: 1900,
        },
        {
          id: "zai_glm_coding",
          name: "Z.ai GLM Coding",
          subscription: "GLM Coding Plan",
          monthly_cost: null,
          pricing_status: "official-source-present-cost-unverified",
          role: "cheap_bulk_transform",
          category: "subscription",
          status: "handoff_only",
          provider_state: "handoff_only",
          state_reasons: ["handoff_only_execution_path"],
          execution_mode: "handoff_bundle",
          direct_execution_ready: false,
          governed_handoff_ready: true,
          available: false,
          tasks_today: 0,
          quota_remaining: null,
          last_used: null,
          avg_latency_ms: null,
        },
      ],
      count: 6,
    };
  }

  if (method === "GET" && basePath === "/v1/subscriptions/summary") {
    return {
      policy_source: "fixture-policy",
      provider_summaries: [
        {
          provider: "anthropic_claude_code",
          label: "Claude Code",
          subscription_product: "Claude Max",
          catalog_monthly_cost_usd: 200,
          catalog_pricing_status: "official_verified",
          lane: "frontier_supervisor",
          availability: "available",
          provider_state: "available",
          reserve_state: "interactive_reserve",
          execution_mode: "direct_cli",
          direct_execution_ready: true,
          governed_handoff_ready: true,
          limit: 25,
          remaining: 18,
          throttle_events: 0,
          recent_outcomes: [
            { outcome: "success", count: 9 },
            { outcome: "review", count: 4 },
          ],
          last_issued_at: "2026-03-11T18:40:00Z",
          last_outcome_at: "2026-03-11T18:47:00Z",
        },
        {
          provider: "openai_codex",
          label: "OpenAI Codex",
          subscription_product: "ChatGPT Pro",
          catalog_monthly_cost_usd: 200,
          catalog_pricing_status: "official_verified",
          lane: "async_backlog_execution",
          availability: "available",
          provider_state: "available",
          reserve_state: "async_reserve",
          execution_mode: "direct_cli",
          direct_execution_ready: true,
          governed_handoff_ready: true,
          limit: 12,
          remaining: 9,
          throttle_events: 0,
          recent_outcomes: [
            { outcome: "success", count: 4 },
            { outcome: "review", count: 1 },
          ],
          last_issued_at: "2026-03-11T18:00:00Z",
          last_outcome_at: "2026-03-11T18:02:00Z",
        },
        {
          provider: "google_gemini",
          label: "Gemini CLI",
          subscription_product: "Google AI Pro / Gemini CLI",
          catalog_monthly_cost_usd: 20,
          catalog_pricing_status: "official_verified",
          lane: "repo_audit_supervisor",
          availability: "available",
          provider_state: "available",
          reserve_state: "analysis_reserve",
          execution_mode: "handoff_bundle",
          direct_execution_ready: false,
          governed_handoff_ready: true,
          limit: 30,
          remaining: 23,
          throttle_events: 0,
          recent_outcomes: [
            { outcome: "success", count: 6 },
            { outcome: "queued", count: 2 },
          ],
          last_issued_at: "2026-03-11T17:20:00Z",
          last_outcome_at: "2026-03-11T17:33:00Z",
        },
        {
          provider: "moonshot_kimi",
          label: "Kimi Code",
          subscription_product: "Kimi Membership / Kimi Code",
          catalog_monthly_cost_usd: null,
          catalog_pricing_status: "official-source-present-cost-unverified",
          lane: "search_heavy_planning",
          availability: "available",
          provider_state: "available",
          reserve_state: "research_reserve",
          execution_mode: "direct_cli",
          direct_execution_ready: true,
          governed_handoff_ready: true,
          limit: 15,
          remaining: 11,
          throttle_events: 0,
          recent_outcomes: [
            { outcome: "success", count: 3 },
            { outcome: "review", count: 1 },
          ],
          last_issued_at: "2026-03-11T16:00:00Z",
          last_outcome_at: "2026-03-11T16:10:00Z",
        },
        {
          provider: "zai_glm_coding",
          label: "Z.ai GLM Coding",
          subscription_product: "GLM Coding Plan",
          catalog_monthly_cost_usd: null,
          catalog_pricing_status: "official-source-present-cost-unverified",
          lane: "cheap_bulk_transform",
          availability: "handoff_only",
          provider_state: "handoff_only",
          reserve_state: "bulk_reserve",
          execution_mode: "handoff_bundle",
          direct_execution_ready: false,
          governed_handoff_ready: true,
          limit: 160,
          remaining: 120,
          throttle_events: 0,
          recent_outcomes: [
            { outcome: "queued", count: 2 },
          ],
          last_issued_at: null,
          last_outcome_at: null,
        },
        {
          provider: "athanor_local",
          label: "Athanor Local",
          subscription_product: "Sovereign local cluster",
          catalog_monthly_cost_usd: 0,
          catalog_pricing_status: "not_applicable",
          lane: "default_local_execution",
          availability: "available",
          provider_state: "available",
          reserve_state: "sovereign_default",
          execution_mode: "local_runtime",
          direct_execution_ready: true,
          governed_handoff_ready: false,
          limit: 0,
          remaining: 0,
          throttle_events: 0,
          recent_outcomes: [
            { outcome: "success", count: 14 },
            { outcome: "fallback", count: 3 },
          ],
          last_issued_at: "2026-03-11T18:55:00Z",
          last_outcome_at: "2026-03-11T18:58:00Z",
        },
      ],
      recent_leases: [
        {
          id: "run-fixture-frontier",
          source_lane: "frontier_cloud",
          run_type: "lease",
          task_id: null,
          job_id: "research-fixture-models",
          agent: "research-agent",
          provider: "google_gemini",
          lease_id: "lease-fixture-research",
          status: "success",
          created_at: "2026-03-11T17:20:00Z",
          started_at: "2026-03-11T17:21:00Z",
          completed_at: "2026-03-11T17:33:00Z",
          artifact_refs: [{ label: "backlog", href: "/backlog" }],
          failure_reason: null,
          summary: "repo audit -> provider-backed research",
        },
        {
          id: "run-fixture-local",
          source_lane: "sovereign_local",
          run_type: "lease",
          task_id: "task-fixture-local",
          job_id: null,
          agent: "coding-agent",
          provider: "athanor_local",
          lease_id: "lease-fixture-local",
          status: "success",
          created_at: "2026-03-11T18:50:00Z",
          started_at: "2026-03-11T18:51:00Z",
          completed_at: "2026-03-11T18:58:00Z",
          artifact_refs: [{ label: "runs", href: "/runs" }],
          failure_reason: null,
          summary: "private implementation stayed local",
        },
      ],
      count: 6,
    };
  }

  if (method === "GET" && basePath === "/v1/subscriptions/execution") {
      return {
        generated_at: timestamp,
        policy_source: "fixture-policy",
        adapters: [
          {
            provider: "anthropic_claude_code",
            execution_mode: "direct_cli",
            adapter_available: true,
            supports_handoff: true,
            command_hint: "claude",
            meta_lane: "frontier_cloud",
            availability_state: "available",
            notes: ["Preferred frontier architecture lane."],
          },
          {
            provider: "google_gemini",
            execution_mode: "handoff_bundle",
            adapter_available: false,
            supports_handoff: true,
            command_hint: null,
            meta_lane: "frontier_cloud",
            availability_state: "handoff-only",
            notes: ["Large-context audits currently use structured handoff."],
          },
          {
            provider: "athanor_local",
            execution_mode: "local_runtime",
            adapter_available: true,
            supports_handoff: false,
            command_hint: null,
            meta_lane: "sovereign_local",
            availability_state: "available",
            notes: ["Primary sovereign execution lane."],
          },
        ],
      recent_handoffs: [
        {
          id: "handoff-fixture-frontier",
          requester: "research-agent",
          provider: "google_gemini",
          task_class: "repo_wide_audit",
          policy_class: "cloud_safe",
          meta_lane: "frontier_cloud",
          execution_mode: "handoff_bundle",
          created_at: "2026-03-11T17:19:00Z",
          summary: "research-agent -> repo_wide_audit via google_gemini",
          prompt: "Audit the repo and summarize the next implementation batch.",
          prompt_mode: "raw",
          abstract_prompt: null,
          fallback: ["anthropic_claude_code", "athanor_local"],
          command_decision: {
            id: "decision-fixture-frontier",
            decided_by: "Athanor Governor",
            authority_layer: "governor",
            workload_class: "repo_audit",
            policy_class: "cloud_safe",
            meta_lane: "frontier_cloud",
            reason: "requester=research-agent; workload=repo_audit; policy=cloud_safe",
            approved: true,
            created_at: "2026-03-11T17:19:00Z",
          },
          plan_packet: {
            id: "packet-fixture-frontier",
            summary: "Audit the repo and summarize the next implementation batch.",
            workload_class: "repo_audit",
            policy_class: "cloud_safe",
            meta_lane: "frontier_cloud",
            supervisor_lane: "frontier_supervisor",
            worker_lane: "bulk_worker",
            approval_mode: "act_notify",
            notes: ["Requester: research-agent"],
          },
          instructions: ["Open the frontier lane.", "Return structured results."],
          notes: ["Large-context audits currently use structured handoff."],
        },
      ],
      recent_leases: [
        {
          id: "lease-fixture-research",
          requester: "research-agent",
          provider: "google_gemini",
          task_class: "repo_wide_audit",
          expires_at: "2026-03-11T19:00:00Z",
        },
      ],
      count: 3,
      };
    }

  if (method === "POST" && basePath === "/v1/subscriptions/execution") {
    return {
      status: "completed",
      provider: "anthropic_claude_code",
      message: "Fixture provider execution completed.",
      handoff: {
        id: "handoff-fixture-execution",
        requester: typeof payload?.requester === "string" ? payload.requester : "coding-agent",
        provider: "anthropic_claude_code",
        task_class: typeof payload?.task_class === "string" ? payload.task_class : "multi_file_implementation",
        policy_class: "private_but_cloud_allowed",
        meta_lane: "frontier_cloud",
        execution_mode: "direct_cli",
        created_at: timestamp,
        updated_at: timestamp,
        completed_at: timestamp,
        status: "completed",
        outcome: "completed",
        summary: "fixture provider execution",
        prompt: typeof payload?.prompt === "string" ? payload.prompt : "fixture prompt",
        prompt_mode: "raw",
        abstract_prompt: null,
        fallback: ["athanor_local"],
        result_summary: "Fixture direct provider execution succeeded.",
        artifact_refs: [{ label: "agents", href: "/agents" }],
      },
      execution: {
        ok: true,
        execution_mode: "direct_cli",
        duration_ms: 4200,
        summary: "Fixture direct provider execution succeeded.",
      },
      adapter: {
        provider: "anthropic_claude_code",
        execution_mode: "direct_cli",
        adapter_available: true,
        supports_handoff: true,
        command_hint: "claude",
        meta_lane: "frontier_cloud",
        availability_state: "available",
      },
    };
  }

  if (method === "GET" && basePath === "/v1/subscriptions/handoffs") {
    return {
      handoffs: [
        {
          id: "handoff-fixture-frontier",
          requester: "research-agent",
          provider: "google_gemini",
          task_class: "repo_wide_audit",
          policy_class: "cloud_safe",
          meta_lane: "frontier_cloud",
          execution_mode: "handoff_bundle",
          created_at: "2026-03-11T17:19:00Z",
          summary: "research-agent -> repo_wide_audit via google_gemini",
          prompt: "Audit the repo and summarize the next implementation batch.",
          prompt_mode: "raw",
          abstract_prompt: null,
          fallback: ["anthropic_claude_code", "athanor_local"],
          command_decision: {
            id: "decision-fixture-frontier",
            decided_by: "Athanor Governor",
            authority_layer: "governor",
            workload_class: "repo_audit",
            policy_class: "cloud_safe",
            meta_lane: "frontier_cloud",
            reason: "requester=research-agent; workload=repo_audit; policy=cloud_safe",
            approved: true,
            created_at: "2026-03-11T17:19:00Z",
          },
          plan_packet: {
            id: "packet-fixture-frontier",
            summary: "Audit the repo and summarize the next implementation batch.",
            workload_class: "repo_audit",
            policy_class: "cloud_safe",
            meta_lane: "frontier_cloud",
            supervisor_lane: "frontier_supervisor",
            worker_lane: "bulk_worker",
            approval_mode: "act_notify",
            notes: ["Requester: research-agent"],
          },
          instructions: ["Open the frontier lane.", "Return structured results."],
          notes: ["Large-context audits currently use structured handoff."],
        },
      ],
      count: 1,
    };
  }

  if (method === "POST" && basePath === "/v1/subscriptions/handoffs") {
    return {
      handoff: {
        id: "handoff-fixture-new",
        requester: typeof payload?.requester === "string" ? payload.requester : "coding-agent",
        provider: "anthropic_claude_code",
        task_class: typeof payload?.task_class === "string" ? payload.task_class : "multi_file_implementation",
        policy_class: "private_but_cloud_allowed",
        meta_lane: "frontier_cloud",
        execution_mode: "handoff_bundle",
        created_at: timestamp,
        summary: "fixture handoff bundle",
        prompt: typeof payload?.prompt === "string" ? payload.prompt : "fixture prompt",
        prompt_mode: "raw",
        abstract_prompt: null,
        fallback: ["athanor_local"],
        command_decision: {
          id: "decision-fixture-new",
          decided_by: "Athanor Governor",
          authority_layer: "governor",
          workload_class: typeof payload?.task_class === "string" ? payload.task_class : "coding_implementation",
          policy_class: "private_but_cloud_allowed",
          meta_lane: "frontier_cloud",
          reason: "fixture decision",
          approved: true,
          created_at: timestamp,
        },
        plan_packet: {
          id: "packet-fixture-new",
          summary: typeof payload?.prompt === "string" ? payload.prompt : "fixture prompt",
          workload_class: typeof payload?.task_class === "string" ? payload.task_class : "coding_implementation",
          policy_class: "private_but_cloud_allowed",
          meta_lane: "frontier_cloud",
          supervisor_lane: "frontier_supervisor",
          worker_lane: "coding_worker",
          approval_mode: "propose_wait",
          notes: ["Fixture plan packet"],
        },
        instructions: ["Use the bundle and return structured results."],
        notes: ["Fixture-generated handoff bundle"],
      },
    };
  }

  if (method === "GET" && basePath === "/v1/models/governance") {
    return {
      generated_at: timestamp,
      role_registry_version: "2026-03-12",
      workload_registry_version: "2026-03-12",
      rights_registry_version: "2026-03-12",
      policy_registry_version: "2026-03-12",
      role_count: 4,
      workload_count: 3,
      champion_summary: [
        {
          role_id: "frontier_supervisor",
          label: "Frontier supervisor",
          plane: "frontier_cloud",
          status: "live",
          champion: "Claude",
          challenger_count: 4,
          workload_count: 5,
        },
        {
          role_id: "sovereign_supervisor",
          label: "Sovereign supervisor",
          plane: "sovereign_local",
          status: "live",
          champion: "reasoning",
          challenger_count: 2,
          workload_count: 4,
        },
        {
          role_id: "coding_worker",
          label: "Coding worker",
          plane: "local_worker",
          status: "live",
          champion: "coding",
          challenger_count: 2,
          workload_count: 3,
        },
        {
          role_id: "judge_verifier",
          label: "Judge / verifier",
          plane: "local_judge",
          status: "live",
          champion: "judge-local-v1",
          challenger_count: 1,
          workload_count: 3,
        },
      ],
      role_registry: [
        {
          id: "frontier_supervisor",
          label: "Frontier supervisor",
          plane: "frontier_cloud",
          status: "live",
          champion: "Claude",
          challengers: ["Codex", "Gemini", "Kimi", "GLM"],
          workload_classes: ["architecture_planning", "repo_audit", "code_review", "research_synthesis", "briefing_digest"],
          strengths: ["large-context planning", "cross-repo critique", "strategic decomposition"],
          weaknesses: ["refusal-sensitive work", "provider limits", "privacy boundaries"],
          refusal_posture: "provider-governed",
          privacy_posture: "cloud_safe_or_abstracted_only",
        },
        {
          id: "sovereign_supervisor",
          label: "Sovereign supervisor",
          plane: "sovereign_local",
          status: "live",
          champion: "reasoning",
          challengers: ["coding", "uncensored"],
          workload_classes: ["private_automation", "refusal_sensitive_creative", "explicit_dialogue", "sovereign_planning"],
          strengths: ["privacy", "uncensored continuity", "refusal resilience"],
          weaknesses: ["weaker frontier reasoning", "higher local contention"],
          refusal_posture: "operator-governed",
          privacy_posture: "local_only",
        },
        {
          id: "coding_worker",
          label: "Coding worker",
          plane: "local_worker",
          status: "live",
          champion: "coding",
          challengers: ["coder", "worker"],
          workload_classes: ["coding_implementation", "repo_mutation", "test_fixing"],
          strengths: ["bulk code generation", "iterative edits", "private repo work"],
          weaknesses: ["broad architectural judgment"],
          refusal_posture: "local",
          privacy_posture: "local_default",
        },
        {
          id: "judge_verifier",
          label: "Judge / verifier",
          plane: "local_judge",
          status: "live",
          champion: "judge-local-v1",
          challengers: ["critic-local-v1"],
          workload_classes: ["judge_verification", "promotion_gating", "regression_scoring"],
          strengths: ["rubric scoring", "lane comparison", "promotion gating"],
          weaknesses: ["not an execution lane"],
          refusal_posture: "local",
          privacy_posture: "local_only",
        },
      ],
      workload_registry: [
        {
          id: "architecture_planning",
          label: "Architecture planning",
          policy_default: "cloud_safe",
          frontier_supervisor: "frontier_supervisor",
          sovereign_supervisor: "sovereign_supervisor",
          primary_worker_lane: "coding_worker",
          fallback_worker_lanes: ["bulk_worker"],
          judge_lane: "judge_verifier",
          default_autonomy: "C",
          parallelism: "manager_first",
        },
        {
          id: "coding_implementation",
          label: "Coding implementation",
          policy_default: "private_but_cloud_allowed",
          frontier_supervisor: "frontier_supervisor",
          sovereign_supervisor: "sovereign_supervisor",
          primary_worker_lane: "coding_worker",
          fallback_worker_lanes: ["bulk_worker"],
          judge_lane: "judge_verifier",
          default_autonomy: "C",
          parallelism: "manager_first",
        },
        {
          id: "refusal_sensitive_creative",
          label: "Refusal-sensitive creative generation",
          policy_default: "refusal_sensitive",
          frontier_supervisor: "frontier_supervisor",
          sovereign_supervisor: "sovereign_supervisor",
          primary_worker_lane: "creative_worker",
          fallback_worker_lanes: ["bulk_worker"],
          judge_lane: "judge_verifier",
          default_autonomy: "D",
          parallelism: "manager_first",
        }
      ],
      proving_ground: {
        version: "2026-03-12",
        updated_at: "2026-03-12T06:20:00Z",
        status: "live",
        purpose: "Continuously prove which models, prompts, policies, and pipelines are best for Athanor.",
        evaluation_dimensions: [
          "functional_quality",
          "operational_quality",
          "behavioral_quality",
          "refusal_and_sovereignty",
          "judge_scores"
        ],
        corpora: [
          {
            id: "golden_tasks",
            sensitivity: "mixed",
            allowed_lanes: ["frontier_cloud", "sovereign_local", "local_worker"],
            purpose: "core Athanor workload regressions and champion/challenger comparisons"
          },
          {
            id: "private_local_only",
            sensitivity: "private",
            allowed_lanes: ["sovereign_local", "local_worker", "local_judge"],
            purpose: "private automation and local-only workflow packs"
          }
        ],
        pipeline_phases: ["intake", "benchmark", "functional_eval", "policy_eval", "shadow", "canary", "promotion_review"],
        promotion_path: ["horizon_scan", "candidate_triage", "offline_eval", "refusal_privacy_eval", "shadow_run", "canary_run", "operator_review", "promote_or_reject"],
        rollback_rule: "keep previous champion available until canary and operator review succeed"
      },
      promotion_controls: buildFixturePromotionControls(timestamp, promotionState),
      retirement_controls: buildFixtureRetirementControls(timestamp, retirementState),
      model_intelligence: {
        version: "2026-03-12",
        updated_at: "2026-03-12T06:20:00Z",
        status: "live_partial",
        generated_at: timestamp,
        operational_state: "seeded",
        cadence: {
          weekly_horizon_scan: "every Monday",
          weekly_candidate_triage: "every Tuesday",
          monthly_rebaseline: "first Saturday of the month",
          urgent_scan: "major model or inference-engine release"
        },
        sources: [
          "vendor release notes",
          "LiteLLM release notes",
          "vLLM release notes",
          "Hugging Face watchlists",
          "Athanor runtime traces"
        ],
        outputs: [
          "candidate intake brief",
          "champion challenger queue",
          "promotion or retirement recommendation"
        ],
        guardrails: [
          "do not promote on public hype alone",
          "refusal-sensitive candidates must be tested locally",
          "keep the previous champion available for rollback"
        ],
        benchmark_results: 12,
        pending_proposals: 2,
        validated_proposals: 1,
        deployed_proposals: 1,
        cadence_jobs: [
          {
            id: "agent-schedule:research-agent",
            title: "Weekly horizon scan posture",
            cadence: "2h",
            current_state: "scheduled",
            last_run: "2026-03-12T04:00:00Z",
            next_run: "2026-03-12T06:00:00Z",
            last_outcome: "completed",
            paused: false,
            governor_reason: null,
          },
          {
            id: "benchmark-cycle",
            title: "Monthly champion rebaseline posture",
            cadence: "every 6h",
            current_state: "scheduled",
            last_run: "2026-03-12T00:00:00Z",
            next_run: "2026-03-12T06:00:00Z",
            last_outcome: "completed",
            paused: false,
            governor_reason: null,
          },
          {
            id: "improvement-cycle",
            title: "Weekly candidate triage posture",
            cadence: "daily 5:30",
            current_state: "scheduled",
            last_run: "2026-03-12T05:30:00Z",
            next_run: "2026-03-13T05:30:00Z",
            last_outcome: "completed",
            paused: false,
            governor_reason: null,
          },
        ],
        candidate_queue: [
          {
            role_id: "frontier_supervisor",
            label: "Frontier supervisor",
            plane: "frontier_cloud",
            champion: "Claude",
            challengers: ["Codex", "Gemini"],
          },
        ],
        last_cycle: {
          timestamp: "2026-03-12T05:30:00Z",
          patterns_consumed: 2,
          proposals_generated: 1,
          benchmarks: {
            passed: 4,
            total: 5,
            pass_rate: 0.8,
          },
          errors: [],
        },
        next_actions: [
          "Review the current frontier supervisor challenger queue.",
          "Rebaseline sovereign supervisor candidates after the next benchmark cycle.",
        ],
      }
    };
  }

  if (method === "GET" && basePath === "/v1/models/proving-ground") {
    return {
      generated_at: timestamp,
      version: "2026-03-12",
      status: "live",
      purpose: "Continuously prove which models, prompts, policies, and pipelines are best for Athanor.",
      evaluation_dimensions: [
        "functional_quality",
        "operational_quality",
        "behavioral_quality",
        "refusal_and_sovereignty",
        "judge_scores",
      ],
      corpora: [
        {
          id: "golden_tasks",
          sensitivity: "mixed",
          allowed_lanes: ["frontier_cloud", "sovereign_local", "local_worker"],
          purpose: "core Athanor workload regressions and champion/challenger comparisons",
        },
        {
          id: "refusal_sensitive",
          sensitivity: "sovereign_only",
          allowed_lanes: ["sovereign_local", "local_worker", "local_judge"],
          purpose: "uncensored or provider-hostile workload packs",
        },
      ],
      pipeline_phases: ["intake", "benchmark", "functional_eval", "policy_eval", "shadow", "canary", "promotion_review"],
      promotion_path: ["horizon_scan", "candidate_triage", "offline_eval", "refusal_privacy_eval", "shadow_run", "canary_run", "operator_review", "promote_or_reject"],
      rollback_rule: "keep previous champion available until canary and operator review succeed",
      latest_run: {
        timestamp: "2026-03-11T18:45:00Z",
        passed: 4,
        total: 5,
        pass_rate: 0.8,
        patterns_consumed: 2,
        proposals_generated: 1,
        errors: [],
        source: "improvement_cycle",
      },
      recent_results: [
        {
          benchmark_id: "routing_accuracy:task_classification",
          category: "routing_accuracy",
          name: "task_classification",
          score: 83.0,
          max_score: 100.0,
          passed: true,
          timestamp: "2026-03-11T18:45:00Z",
          details: { sample: "fixture" },
          duration_ms: 44.0,
        },
        {
          benchmark_id: "inference_latency:reasoning_latency",
          category: "inference_latency",
          name: "reasoning_latency",
          score: 72.0,
          max_score: 100.0,
          passed: false,
          timestamp: "2026-03-11T18:44:00Z",
          details: { latency_ms: 2140 },
          duration_ms: 2140.0,
        },
      ],
      improvement_summary: {
        total_proposals: 3,
        pending: 1,
        validated: 1,
        deployed: 1,
        failed: 0,
        archive_entries: 0,
        benchmark_results: 5,
        latest_baseline: {
          "routing_accuracy:task_classification": 83.0,
          "inference_latency:reasoning_latency": 72.0,
        },
        last_cycle: {
          timestamp: "2026-03-11T18:45:00Z",
          benchmarks: { passed: 4, total: 5, pass_rate: 0.8 },
          patterns_consumed: 2,
          proposals_generated: 1,
          errors: [],
        },
      },
      lane_coverage: [
        {
          role_id: "frontier_supervisor",
          label: "Frontier supervisor",
          plane: "frontier_cloud",
          status: "live",
          champion: "Claude",
          challenger_count: 4,
          workload_count: 5,
        },
        {
          role_id: "sovereign_supervisor",
          label: "Sovereign supervisor",
          plane: "sovereign_local",
          status: "live",
          champion: "reasoning",
          challenger_count: 2,
          workload_count: 4,
        },
      ],
      promotion_controls: buildFixturePromotionControls(timestamp, promotionState),
    };
  }

    if (method === "GET" && basePath === "/v1/models/governance/promotions") {
      return buildFixturePromotionControls(timestamp, promotionState);
    }

    if (method === "GET" && basePath === "/v1/models/governance/retirements") {
      return buildFixtureRetirementControls(timestamp, retirementState);
    }

  if (method === "GET" && basePath === "/v1/activity/operator-stream") {
    return {
      events: [
        {
          id: "event-fixture-run",
          timestamp: "2026-03-11T18:58:00Z",
          severity: "success",
          subsystem: "tasks",
          event_type: "run_completed",
          subject: "coding-agent",
          summary: "Private implementation completed via athanor_local.",
          deep_link: "/runs",
          related_run_id: "run-fixture-local",
        },
        {
          id: "event-fixture-research",
          timestamp: "2026-03-11T17:33:00Z",
          severity: "info",
          subsystem: "provider-plane",
          event_type: "lease_review",
          subject: "research-agent",
          summary: "Repo audit used frontier planning and returned a review packet.",
          deep_link: "/backlog",
          related_run_id: "run-fixture-frontier",
        },
        {
          id: "event-fixture-alert",
          timestamp: "2026-03-11T17:10:00Z",
          severity: "warning",
          subsystem: "alerts",
          event_type: "provider_posture",
          subject: "subscription-broker",
          summary: "Interactive reserve remains healthy across frontier providers.",
          deep_link: "/inbox",
          related_run_id: null,
        },
      ],
      count: 3,
    };
  }

  if (method === "GET" && basePath === "/v1/tasks/runs") {
    return {
      runs: [
        {
          id: "run-fixture-local",
          source_lane: "sovereign_local",
          run_type: "task",
          task_id: "task-fixture-local",
          job_id: null,
          agent: "coding-agent",
          provider: "athanor_local",
          lease_id: "lease-fixture-local",
          status: "completed",
          created_at: "2026-03-11T18:50:00Z",
          started_at: "2026-03-11T18:51:00Z",
          completed_at: "2026-03-11T18:58:00Z",
          artifact_refs: [{ label: "runs", href: "/runs" }],
          failure_reason: null,
          summary: "private implementation stayed local",
        },
        {
          id: "run-fixture-frontier",
          source_lane: "frontier_cloud",
          run_type: "research_job",
          task_id: null,
          job_id: "research-fixture-models",
          agent: "research-agent",
          provider: "google_gemini",
          lease_id: "lease-fixture-research",
          status: "completed",
          created_at: "2026-03-11T17:20:00Z",
          started_at: "2026-03-11T17:21:00Z",
          completed_at: "2026-03-11T17:33:00Z",
          artifact_refs: [{ label: "backlog", href: "/backlog" }],
          failure_reason: null,
          summary: "repo audit -> provider-backed research",
        },
      ],
      count: 2,
    };
  }

  if (method === "GET" && basePath === "/v1/tasks/scheduled") {
    return {
      jobs: [
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
        },
        {
          id: "research:research-fixture-models",
          job_family: "research_job",
          title: "Subscription provider utilization",
          cadence: "every 24h",
          trigger_mode: "interval",
          last_run: "2026-03-11T17:33:00Z",
          next_run: "2026-03-12T17:33:00Z",
          current_state: "deferred",
          last_outcome: "completed",
          owner_agent: "research-agent",
          deep_link: "/backlog",
          control_scope: "research_jobs",
          paused: false,
          can_run_now: false,
          can_override_now: true,
          governor_reason: "Governor deferred this research run while the operator is away.",
          last_summary: "Most recent research run completed and published findings.",
          last_error: null,
        },
      ],
      count: 2,
    };
  }

  if (method === "POST" && /\/v1\/tasks\/scheduled\/.+\/run$/.test(basePath)) {
    const segments = basePath.split("/");
    const jobId = decodeURIComponent(segments[segments.length - 2] ?? "scheduled-job");
    const body = parseFixtureBody(init?.body);
    const force = Boolean(body?.force);
    if (jobId === "research:research-fixture-models" && !force) {
      return {
        job_id: jobId,
        status: "deferred",
        summary: "Governor deferred manual run for research:research-fixture-models: operator is away.",
        governor_decision: {
          status: "deferred",
          reason: "Governor deferred this research run while the operator is away.",
        },
        override_available: true,
      };
    }
    return {
      job_id: jobId,
      status: "queued",
      summary: force
        ? `Fixture scheduled job ${jobId} triggered with operator override.`
        : `Fixture scheduled job ${jobId} triggered.`,
    };
  }

  if (method === "GET" && basePath === "/v1/system-map") {
    return {
      generated_at: timestamp,
      owner: {
        id: "shaun",
        label: "Shaun",
        role: "owner",
      },
      constitution: {
        label: "Constitution + policy registry",
        source: "CONSTITUTION.yaml + policy files",
        enforcement: "highest_non_human_authority",
      },
      governor: {
        label: "Athanor governor",
        role: "runtime commander of record",
        status: "live",
        rights: [
          "create durable tasks",
          "issue execution leases",
          "schedule recurring jobs",
          "pause or resume automation",
          "choose fallback or degraded mode",
        ],
      },
      authority_order: [
        {
          id: "shaun",
          label: "Shaun",
          role: "owner",
          summary: "Final authority for approvals, priorities, and irreversible changes.",
        },
        {
          id: "constitution",
          label: "Constitution + Policy Registry",
          role: "highest_non_human_authority",
          summary: "Immutable constraints, cloud boundaries, and approval rules.",
        },
        {
          id: "governor",
          label: "Athanor Governor",
          role: "runtime_commander",
          summary: "Owns durable tasks, leases, schedules, and degraded-mode choice.",
        },
        {
          id: "meta_strategy",
          label: "Meta Strategy Layer",
          role: "planning_review",
          summary: "Frontier and sovereign supervisors that plan and review without direct runtime mutation.",
        },
        {
          id: "control_stack",
          label: "Orchestrator Control Stack",
          role: "execution_control",
          summary: "Server, router, tasks, scheduler, workspace, workplanner, alerts, subscriptions, and capacity arbitration.",
        },
        {
          id: "specialists",
          label: "Specialist Agents",
          role: "domain_execution",
          summary: "Domain-scoped execution agents operating inside tool and approval boundaries.",
        },
        {
          id: "workers_judges",
          label: "Worker and Judge Planes",
          role: "generation_and_scoring",
          summary: "Bulk local execution and verification lanes with no command rights.",
        },
        {
          id: "tools_infra",
          label: "Tools and Infrastructure",
          role: "governed_resources",
          summary: "Repos, services, models, stores, and adapters that never act as free decision-makers.",
        },
      ],
      meta_lanes: [
        {
          id: "frontier_cloud",
          label: "Frontier Cloud Meta Lead",
          lead: "Claude",
          default_for: ["cloud_safe", "private_but_cloud_allowed", "hybrid_abstractable"],
          cloud_allowed: true,
          status: "live",
          examples: ["anthropic_claude_code", "google_gemini", "openai_codex"],
        },
        {
          id: "sovereign_local",
          label: "Sovereign Local Meta Lead",
          lead: "Local sovereign supervisor",
          default_for: ["refusal_sensitive", "sovereign_only"],
          cloud_allowed: false,
          status: "live",
          examples: ["reasoning", "coding", "uncensored"],
        },
      ],
      control_stack: [
        {
          id: "agent-server",
          label: "Agent Server",
          role: "runtime boundary and API front door",
          entrypoints: ["/health", "/v1/chat/completions", "/v1/agents", "/v1/models"],
          status: "live",
        },
        {
          id: "router",
          label: "Router",
          role: "processing-tier and workload triage",
          entrypoints: ["/v1/routing/classify"],
          status: "live",
        },
        {
          id: "task-engine",
          label: "Task Engine",
          role: "durable queued work and approvals",
          entrypoints: ["/v1/tasks", "/v1/tasks/runs"],
          status: "live",
        },
        {
          id: "scheduler",
          label: "Scheduler",
          role: "recurring loops and schedule introspection",
          entrypoints: ["/v1/tasks/scheduled", "/v1/scheduling/status"],
          status: "live",
        },
        {
          id: "workspace",
          label: "Workspace / GWT",
          role: "shared attention and broadcast arbitration",
          entrypoints: ["/v1/workspace", "/v1/workspace/stats"],
          status: "live",
        },
      ],
      specialists: [
        {
          id: "general-assistant",
          label: "General Assistant",
          role: "read-mostly ops, status, and triage",
          authority: "read, report, delegate",
          tool_count: 8,
          mode: "proactive",
          status: "live",
        },
        {
          id: "coding-agent",
          label: "Coding Agent",
          role: "repo mutation, testing, and controlled code execution",
          authority: "write inside governed repo and task bounds",
          tool_count: 8,
          mode: "proactive",
          status: "live",
        },
        {
          id: "research-agent",
          label: "Research Agent",
          role: "external research and synthesis",
          authority: "research, summarize, request lease",
          tool_count: 5,
          mode: "reactive",
          status: "live",
        },
      ],
      model_planes: [
        {
          id: "frontier_cloud",
          label: "Frontier Cloud Meta Lane",
          role: "best-in-class planning, architecture, critique, and review for allowed workloads",
          status: "live",
        },
        {
          id: "sovereign_local",
          label: "Sovereign Local Meta Lane",
          role: "private, uncensored, refusal-resilient supervision for protected workloads",
          status: "live",
        },
        {
          id: "local_worker_plane",
          label: "Local Worker Plane",
          role: "bulk execution, background loops, transforms, and private local work",
          status: "live",
        },
        {
          id: "local_judge_plane",
          label: "Judge and Verifier Plane",
          role: "score quality, regressions, and promotions without command rights",
          status: "live",
        },
      ],
      command_rights: [
        {
          subject: "Shaun",
          can: ["approve", "override", "change policy", "authorize destructive work"],
          cannot: [],
          approval_mode: "final_authority",
        },
        {
          subject: "Athanor Governor",
          can: ["route work", "create durable tasks", "issue leases", "pause or resume automation"],
          cannot: ["override constitution", "self-authorize forbidden work"],
          approval_mode: "policy_bound_runtime_control",
        },
        {
          subject: "Meta Lanes",
          can: ["plan", "decompose", "review", "recommend redirects"],
          cannot: ["directly run tools", "issue leases", "schedule jobs", "mutate infrastructure"],
          approval_mode: "advisory_only",
        },
      ],
      policy_classes: [
        {
          id: "cloud_safe",
          label: "Cloud safe",
          default_meta_lane: "frontier_cloud",
          cloud_allowed: true,
          sovereign_required: false,
          description: "Safe for frontier planning, review, or execution according to workload policy.",
        },
        {
          id: "hybrid_abstractable",
          label: "Hybrid abstractable",
          default_meta_lane: "frontier_cloud",
          cloud_allowed: true,
          sovereign_required: true,
          description: "Cloud may see an abstracted plan; raw sensitive content stays local.",
        },
        {
          id: "refusal_sensitive",
          label: "Refusal sensitive",
          default_meta_lane: "sovereign_local",
          cloud_allowed: false,
          sovereign_required: true,
          description: "Likely provider-refused or fragile content that should stay on the sovereign lane.",
        },
        {
          id: "sovereign_only",
          label: "Sovereign only",
          default_meta_lane: "sovereign_local",
          cloud_allowed: false,
          sovereign_required: true,
          description: "Never leaves the local cluster because of privacy, refusal risk, or explicit-content rules.",
        },
      ],
      registry_versions: {
        command_rights: "2026-03-12",
        policy_classes: "2026-03-12",
      },
      workload_guidance: [
        {
          id: "research_parallel",
          label: "Research, broad exploration, and synthesis",
          strategy: "manager_supervisor_plus_parallel_subagents",
          supervisor_lane: "frontier_cloud",
          worker_lane: "local_worker_plane",
          judge_lane: "local_judge_plane",
        },
        {
          id: "coding_tight",
          label: "Tightly coupled coding or infrastructure changes",
          strategy: "manager_first_tight_hierarchy",
          supervisor_lane: "frontier_cloud_or_sovereign_by_policy",
          worker_lane: "coding_worker_plane",
          judge_lane: "local_judge_plane",
        },
        {
          id: "sovereign_content",
          label: "Uncensored, explicit, or refusal-sensitive content",
          strategy: "sovereign_supervisor_plus_local_workers",
          supervisor_lane: "sovereign_local",
          worker_lane: "uncensored_local_plane",
          judge_lane: "local_judge_plane",
        },
      ],
      policy_source: "fixture-policy",
    };
  }

  if (method === "GET" && basePath === "/v1/governor") {
    return buildFixtureGovernorSnapshot(governorState, timestamp);
  }

  if (method === "GET" && basePath === "/v1/governor/operations") {
      return buildFixtureOperationsReadinessSnapshot(timestamp, operatorTestsState, retirementState);
  }

  if (method === "GET" && basePath === "/v1/governor/operator-tests") {
    return {
      generated_at: timestamp,
      status:
        operatorTestsState.last_outcome === "failed"
          ? "degraded"
          : operatorTestsState.last_run_at
            ? "live_partial"
            : "configured",
      last_outcome: operatorTestsState.last_outcome,
      last_run_at: operatorTestsState.last_run_at,
      flow_count: operatorTestsState.flows.length,
      flows: operatorTestsState.flows,
    };
  }

  if (method === "POST" && basePath === "/v1/governor/operator-tests/run") {
    operatorTestsState.last_run_at = timestamp;
    operatorTestsState.last_outcome = "partial";
    retirementState.records = [
      {
        id: "retirement-frontier-claude",
        asset_class: "models",
        asset_id: "frontier_supervisor:Claude",
        label: "Frontier supervisor champion Claude",
        current_stage: "active",
        target_stage: "retired_reference_only",
        status: "rolled_back",
        reason: "Fixture retirement rehearsal completed and rolled back safely.",
        created_at: timestamp,
        updated_at: timestamp,
        updated_by: "fixture-operator",
        source: "fixture_operator_tests",
        next_stage: null,
        completed_at: timestamp,
        rollback_target: "active",
        notes: [
          "Fixture retirement rehearsal advanced through deprecated posture before rolling back to active.",
        ],
      },
    ];
    retirementState.events = [
      {
        event: "retirement_staged",
        retirement_id: "retirement-frontier-claude",
        asset_class: "models",
        asset_id: "frontier_supervisor:Claude",
        target_stage: "retired_reference_only",
        timestamp,
        actor: "fixture-operator",
      },
      {
        event: "retirement_advanced",
        retirement_id: "retirement-frontier-claude",
        asset_class: "models",
        asset_id: "frontier_supervisor:Claude",
        stage: "deprecated",
        status: "active",
        timestamp,
        actor: "fixture-operator",
      },
      {
        event: "retirement_advanced",
        retirement_id: "retirement-frontier-claude",
        asset_class: "models",
        asset_id: "frontier_supervisor:Claude",
        stage: "retired_reference_only",
        status: "completed",
        timestamp,
        actor: "fixture-operator",
      },
      {
        event: "retirement_rolled_back",
        retirement_id: "retirement-frontier-claude",
        asset_class: "models",
        asset_id: "frontier_supervisor:Claude",
        stage: "active",
        status: "rolled_back",
        timestamp,
        actor: "fixture-operator",
      },
    ];
    operatorTestsState.flows = operatorTestsState.flows.map((flow) => {
      if (flow.id === "restore_drill") {
        return {
          ...flow,
          status: "live_partial",
          last_outcome: "passed",
          last_run_at: timestamp,
          last_duration_ms: 42,
          checks_passed: 4,
          checks_total: 4,
          notes: [
            "Restore drill captured live non-destructive evidence against all critical stores.",
          ],
          details: {
            drill_mode: "non_destructive_live_probe",
            verified_store_count: 4,
            store_count: 4,
            stores: [
              {
                id: "redis_critical_state",
                label: "Redis critical state",
                verified: true,
                probe_status: "verified",
                probe_summary: "Redis ping and synthetic write/read/delete rehearsal succeeded.",
                checked_at: timestamp,
              },
              {
                id: "qdrant_memory",
                label: "Qdrant memory",
                verified: true,
                probe_status: "verified",
                probe_summary: "Qdrant collections endpoint is healthy and visible to the rehearsal flow.",
                checked_at: timestamp,
              },
              {
                id: "neo4j_graph",
                label: "Neo4j graph",
                verified: true,
                probe_status: "verified",
                probe_summary: "Neo4j authenticated probe succeeded with a minimal read-only transaction.",
                checked_at: timestamp,
              },
              {
                id: "dashboard_agent_deploy_state",
                label: "Dashboard and agent deployment state",
                verified: true,
                probe_status: "verified",
                probe_summary: "Agent and dashboard deployment surfaces are reachable for ordered recovery.",
                checked_at: timestamp,
              },
            ],
          },
        };
      }
      const livePartialIds = new Set([
        "provider_fallback",
        "stuck_queue_recovery",
        "incident_review",
        "tool_permissions",
        "economic_governance",
        "promotion_ladder",
        "retirement_policy",
        "data_lifecycle",
      ]);
      const detailsByFlow: Record<string, Record<string, unknown>> = {
        provider_fallback: {
          adapter_count: 6,
          recent_lease_count: 10,
        },
        stuck_queue_recovery: {
          scheduler_job_count: 5,
          run_count: 12,
          queue_posture: "healthy",
        },
        incident_review: {
          active_alert_count: 1,
          alert_history_count: 2,
          stream_event_count: 6,
          run_count: 12,
        },
        tool_permissions: {
          subject_count: 4,
          enforced_subject_count: 4,
          denied_action_count: 3,
        },
        economic_governance: {
          provider_count: 6,
          recent_lease_count: 10,
          constrained_count: 1,
        },
        promotion_ladder: {
          promotion_id: "promotion-frontier-gemini",
          role_id: "frontier_supervisor",
          candidate: "Gemini",
          target_tier: "canary",
          traversed_tiers: ["offline_eval", "shadow", "sandbox", "canary"],
          final_status: "rolled_back",
          rollback_target: "Claude",
        },
        retirement_policy: {
          retirement_id: "retirement-frontier-claude",
          asset_class: "models",
          asset_id: "frontier_supervisor:Claude",
          label: "Frontier supervisor champion Claude",
          traversed_stages: ["active", "deprecated", "retired_reference_only"],
          final_status: "rolled_back",
          rollback_target: "active",
        },
        data_lifecycle: {
          class_count: 5,
          run_count: 12,
          eval_artifact_count: 5,
          sovereign_policy_class: "sovereign_only",
          sovereign_meta_lane: "sovereign_local",
        },
      };
      const notesByFlow: Record<string, string[]> = {
        provider_fallback: [
          "Frontier providers remain handoff-first in fixture mode; direct CLI execution is intentionally partial.",
        ],
        stuck_queue_recovery: [
          "Queue-recovery rehearsal paused the scheduler lane, verified queued posture, and restored forward progress cleanly.",
        ],
        incident_review: [
          "Incident review verified alert posture, operator stream visibility, and execution-run lineage together.",
        ],
        retirement_policy: [
          "Retirement rehearsal advanced a governed model asset through deprecated and retired-reference-only posture before rolling back to active.",
        ],
      };
      const livePartial = livePartialIds.has(flow.id);
      return {
        ...flow,
        status: livePartial ? "live_partial" : "live",
        last_outcome: "passed",
        last_run_at: timestamp,
        last_duration_ms: livePartial ? 58 : 31,
        checks_passed: flow.checks_total,
        checks_total: flow.checks_total,
        notes: notesByFlow[flow.id] ?? [],
        details: detailsByFlow[flow.id] ?? flow.details,
      };
    });
    return {
      generated_at: timestamp,
      status: "live_partial",
      last_outcome: operatorTestsState.last_outcome,
      last_run_at: operatorTestsState.last_run_at,
      flow_count: operatorTestsState.flows.length,
      flows: operatorTestsState.flows,
    };
  }

  if (method === "POST" && basePath === "/v1/governor/pause") {
    const scope = typeof payload?.scope === "string" ? payload.scope : "global";
    const actor = typeof payload?.actor === "string" ? payload.actor : "fixture-operator";
    governorState.updated_at = timestamp;
    governorState.updated_by = actor;
    governorState.reason = typeof payload?.reason === "string" ? payload.reason : "";
    if (scope === "global") {
      governorState.global_mode = "paused";
    } else if (!governorState.paused_lanes.includes(scope)) {
      governorState.paused_lanes.push(scope);
      governorState.paused_lanes.sort();
    }
    return buildFixtureGovernorSnapshot(governorState, timestamp);
  }

  if (method === "POST" && basePath === "/v1/governor/resume") {
    const scope = typeof payload?.scope === "string" ? payload.scope : "global";
    const actor = typeof payload?.actor === "string" ? payload.actor : "fixture-operator";
    governorState.updated_at = timestamp;
    governorState.updated_by = actor;
    if (scope === "global") {
      governorState.global_mode = "active";
      governorState.reason = "";
    } else {
      governorState.paused_lanes = governorState.paused_lanes.filter(
        (lane) => lane !== scope
      );
    }
    return buildFixtureGovernorSnapshot(governorState, timestamp);
  }

  if (method === "POST" && basePath === "/v1/governor/presence") {
    const nextState =
      typeof payload?.state === "string" && payload.state in FIXTURE_PRESENCE_PROFILES
        ? (payload.state as keyof typeof FIXTURE_PRESENCE_PROFILES)
        : "at_desk";
    const nextMode =
      payload?.mode === "auto" || payload?.mode === "manual" ? payload.mode : "manual";
    const actor = typeof payload?.actor === "string" ? payload.actor : "fixture-operator";
    governorState.presence_mode = nextMode;
    governorState.presence_reason = typeof payload?.reason === "string" ? payload.reason : "";
    governorState.presence_updated_at = timestamp;
    governorState.presence_updated_by = actor;
    if (nextMode === "manual") {
      governorState.operator_presence = nextState;
    } else {
      governorState.presence_signal_state = nextState;
      governorState.presence_signal_source = "dashboard_heartbeat";
      governorState.presence_signal_reason =
        typeof payload?.reason === "string" && payload.reason
          ? payload.reason
          : "Fixture automatic dashboard heartbeat is active.";
      governorState.presence_signal_updated_at = timestamp;
      governorState.presence_signal_updated_by = actor;
    }
    governorState.updated_at = timestamp;
    governorState.updated_by = actor;
    return buildFixtureGovernorSnapshot(governorState, timestamp);
  }

  if (method === "POST" && basePath === "/v1/governor/heartbeat") {
    const nextState =
      typeof payload?.state === "string" && payload.state in FIXTURE_PRESENCE_PROFILES
        ? (payload.state as keyof typeof FIXTURE_PRESENCE_PROFILES)
        : "at_desk";
    const actor = typeof payload?.actor === "string" ? payload.actor : "dashboard-heartbeat";
    governorState.presence_signal_state = nextState;
    governorState.presence_signal_source =
      typeof payload?.source === "string" && payload.source.trim()
        ? payload.source
        : "dashboard_heartbeat";
    governorState.presence_signal_reason =
      typeof payload?.reason === "string" && payload.reason
        ? payload.reason
        : "Fixture dashboard heartbeat is active.";
    governorState.presence_signal_updated_at = timestamp;
    governorState.presence_signal_updated_by = actor;
    if (governorState.presence_mode !== "manual") {
      governorState.presence_mode = "auto";
      governorState.presence_reason = "Fixture automatic dashboard heartbeat governs presence posture.";
      governorState.presence_updated_at = timestamp;
      governorState.presence_updated_by = actor;
    }
    governorState.updated_at = timestamp;
    governorState.updated_by = actor;
    return buildFixtureGovernorSnapshot(governorState, timestamp);
  }

  if (method === "POST" && basePath === "/v1/governor/release-tier") {
    const nextTier =
      typeof payload?.tier === "string" &&
      ["offline_eval", "shadow", "sandbox", "canary", "production"].includes(payload.tier)
        ? payload.tier
        : "production";
    const actor = typeof payload?.actor === "string" ? payload.actor : "fixture-operator";
    governorState.release_tier = nextTier;
    governorState.tier_reason = typeof payload?.reason === "string" ? payload.reason : "";
    governorState.tier_updated_at = timestamp;
    governorState.tier_updated_by = actor;
    governorState.updated_at = timestamp;
    governorState.updated_by = actor;
    return buildFixtureGovernorSnapshot(governorState, timestamp);
  }

  if (method === "GET" && basePath === "/v1/review/judges") {
    return {
      generated_at: timestamp,
      status: "live",
      role_id: "judge_verifier",
      label: "Judge / verifier",
      champion: "judge-local-v1",
      challengers: ["critic-local-v1"],
      workload_classes: ["judge_verification", "promotion_gating", "regression_scoring"],
      summary: {
        recent_verdicts: 3,
        accept_count: 2,
        reject_count: 1,
        review_required: 0,
        acceptance_rate: 0.67,
        pending_review_queue: 1,
      },
      guardrails: [
        "Judge lanes score and gate; they do not execute production actions.",
        "Protected workloads keep review local when policy is refusal-sensitive or sovereign-only.",
        "Failed runs are not auto-accepted into promotion or automation history.",
      ],
      recent_verdicts: [
        {
          run_id: "run-fixture-frontier",
          agent: "research-agent",
          provider: "google_gemini",
          policy_class: "cloud_safe",
          score: 0.84,
          verdict: "accept",
          rationale: "Execution completed with a durable run record.",
          deep_link: "/runs",
        },
        {
          run_id: "run-fixture-local",
          agent: "coding-agent",
          provider: "athanor_local",
          policy_class: "sovereign_only",
          score: 0.9,
          verdict: "accept",
          rationale: "Execution completed on the sovereign local lane for protected work.",
          deep_link: "/runs",
        },
        {
          run_id: "run-fixture-failed",
          agent: "coding-agent",
          provider: "athanor_local",
          policy_class: "private_but_cloud_allowed",
          score: 0.12,
          verdict: "reject",
          rationale: "Execution failed before a usable result was recorded.",
          deep_link: "/runs",
        },
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

  if (method === "GET" && basePath === "/v1/trust") {
    return {
      generated_at: timestamp,
      agents: {
        "general-assistant": {
          score: 0.94,
          grade: "A",
          feedback: {
            up: 28,
            down: 1,
            total: 29,
          },
          escalation: {
            approved: 12,
            rejected: 1,
            total: 13,
          },
          samples: 29,
        },
        "coding-agent": {
          score: 0.91,
          grade: "A",
          feedback: {
            up: 17,
            down: 2,
            total: 19,
          },
          escalation: {
            approved: 7,
            rejected: 1,
            total: 8,
          },
          samples: 19,
        },
      },
      scores: [
        {
          agent_id: "general-assistant",
          score: 0.94,
          grade: "A",
        },
        {
          agent_id: "coding-agent",
          score: 0.91,
          grade: "A",
        },
      ],
    };
  }

  if (method === "GET" && basePath === "/v1/digests/latest") {
    return {
      type: "auto",
      generated_at: timestamp,
      period: "24h",
      task_count: 6,
      completed_count: 4,
      failed_count: 1,
      recent_completions: [
        {
          id: "task-ath-1",
          title: "Refresh command-center route taxonomy",
          completed_at: isoMinutesBefore(18),
        },
        {
          id: "task-eoq-2",
          title: "Queue new portrait generations",
          completed_at: isoMinutesBefore(43),
        },
      ],
      recent_failures: [
        {
          id: "task-home-1",
          title: "Validate overnight lighting automation",
          failed_at: isoMinutesBefore(61),
        },
      ],
    };
  }

  if (method === "GET" && basePath === "/v1/pipeline/status") {
    return {
      recent_cycles: [
        {
          id: "cycle-2026-03-12T14:45:00Z",
          status: "completed",
          started_at: isoMinutesBefore(22),
          completed_at: isoMinutesBefore(18),
          proposal_count: 3,
        },
      ],
      pending_plans: 1,
      recent_outcomes_count: 5,
      avg_quality: 0.92,
      last_cycle: {
        id: "cycle-2026-03-12T14:45:00Z",
        status: "completed",
        completed_at: isoMinutesBefore(18),
      },
    };
  }

  if (method === "GET" && basePath === "/v1/pipeline/outcomes") {
    const limit = Math.max(Number.parseInt(requestUrl.searchParams.get("limit") ?? "20", 10) || 20, 1);
    const outcomes = [
      {
        id: "outcome-ath-1",
        plan_id: "plan-ath-1",
        status: "accepted",
        quality: 0.94,
        recorded_at: isoMinutesBefore(12),
      },
      {
        id: "outcome-ath-2",
        plan_id: "plan-ath-2",
        status: "review_required",
        quality: 0.81,
        recorded_at: isoMinutesBefore(36),
      },
    ].slice(0, limit);
    return {
      outcomes,
      count: outcomes.length,
    };
  }

  if (method === "GET" && basePath === "/v1/pipeline/plans") {
    const statusFilter = requestUrl.searchParams.get("status");
    const plans = [
      {
        id: "plan-ath-1",
        title: "Promote command-center IA slice to trunk",
        status: "pending",
        created_at: isoMinutesBefore(30),
      },
      {
        id: "plan-ath-2",
        title: "Queue runtime-deploy ansible slice",
        status: "queued",
        created_at: isoMinutesBefore(55),
      },
    ].filter((plan) => !statusFilter || plan.status === statusFilter);
    return {
      plans,
      count: plans.length,
    };
  }

  if (method === "GET" && basePath === "/v1/pipeline/preview") {
    return {
      proposals: [
        {
          id: "proposal-ath-1",
          title: "Commit command-center IA lane",
          confidence: 0.88,
          requires_approval: true,
        },
      ],
      count: 1,
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
      policy_class: "cloud_safe",
      meta_lane: "frontier_cloud",
      cloud_allowed: true,
      requires_sovereign: false,
    };
  }

  if (method === "POST" && path === "/v1/patterns/run") {
    return { ok: true, fixture: true, queued: true, runId: "fixture-pattern-run", timestamp };
  }

  if (method === "POST" && path === "/v1/improvement/benchmarks/run") {
    return { ok: true, fixture: true, queued: true, runId: "fixture-benchmark-run", timestamp };
  }

  if (method === "POST" && path === "/v1/models/proving-ground/run") {
    return {
      generated_at: timestamp,
      version: "2026-03-12",
      status: "live",
      purpose: "Fixture proving ground run",
      evaluation_dimensions: ["functional_quality", "operational_quality"],
      corpora: [],
      pipeline_phases: ["benchmark"],
      promotion_path: ["offline_eval", "operator_review"],
      rollback_rule: "fixture rollback rule",
      latest_run: {
        timestamp,
        passed: 5,
        total: 5,
        pass_rate: 1,
        patterns_consumed: 0,
        proposals_generated: 0,
        errors: [],
        source: "benchmark_history",
      },
      recent_results: [
        {
          benchmark_id: "routing_accuracy:task_classification",
          category: "routing_accuracy",
          name: "task_classification",
          score: 100,
          max_score: 100,
          passed: true,
          timestamp,
          details: { fixture: true },
          duration_ms: 30,
        },
      ],
      improvement_summary: {
        total_proposals: 3,
        pending: 0,
        validated: 1,
        deployed: 2,
        failed: 0,
        archive_entries: 0,
        benchmark_results: 6,
        latest_baseline: {},
        last_cycle: {
          timestamp,
          benchmarks: { passed: 5, total: 5, pass_rate: 1 },
          patterns_consumed: 0,
          proposals_generated: 0,
          errors: [],
        },
      },
      lane_coverage: [],
      latest_benchmark_run: { ok: true, fixture: true, queued: false, timestamp },
    };
  }

  if (method === "POST" && basePath === "/v1/models/governance/promotions") {
    const roleId = typeof payload?.role_id === "string" ? payload.role_id : "frontier_supervisor";
    const candidate = typeof payload?.candidate === "string" ? payload.candidate : "Gemini";
    const targetTier =
      typeof payload?.target_tier === "string" ? payload.target_tier : "canary";
    const actor = typeof payload?.actor === "string" ? payload.actor : "fixture-operator";
    const existing = promotionState.records.find(
      (record) => record.role_id === roleId && record.candidate === candidate && record.status !== "rolled_back"
    );
    if (existing) {
      return { promotion: existing };
    }
    const record: FixturePromotionRecord = {
      id: `promotion-${roleId}-${candidate}`.toLowerCase().replace(/[^a-z0-9-]/g, "-"),
      asset_class: "models",
      role_id: roleId,
      role_label: roleId.replace(/_/g, " "),
      plane: roleId.includes("frontier") ? "frontier_cloud" : "local_worker",
      candidate,
      champion: roleId === "frontier_supervisor" ? "Claude" : "coding",
      current_tier: "offline_eval",
      target_tier: targetTier,
      status: "staged",
      reason:
        typeof payload?.reason === "string" && payload.reason
          ? payload.reason
          : `Fixture staged ${candidate} for ${roleId}.`,
      created_at: timestamp,
      updated_at: timestamp,
      updated_by: actor,
      source: "dashboard_model_governance",
      rollout_steps: buildFixturePromotionControls(timestamp, promotionState).ritual,
      next_tier: "shadow",
      completed_at: null,
      rollback_target: null,
      notes: ["Fixture governed promotion created from the cockpit."],
    };
    promotionState.records.unshift(record);
    promotionState.events.unshift({
      event: "promotion_staged",
      promotion_id: record.id,
      role_id: record.role_id,
      candidate: record.candidate,
      target_tier: record.target_tier,
      timestamp,
      actor,
    });
    return { promotion: record };
  }

  if (method === "POST" && /\/v1\/models\/governance\/promotions\/[^/]+\/(advance|hold|rollback)$/.test(basePath)) {
    const action = basePath.split("/").at(-1) ?? "advance";
    const promotionId = basePath.split("/").at(-2) ?? "";
    const actor = typeof payload?.actor === "string" ? payload.actor : "fixture-operator";
    const record = promotionState.records.find((entry) => entry.id === promotionId);
    if (!record) {
      return { error: `Promotion ${promotionId} not found.`, status: 404 };
    }
    if (action === "advance") {
      const tiers = ["offline_eval", "shadow", "sandbox", "canary", "production"];
      const currentIndex = Math.max(tiers.indexOf(record.current_tier), 0);
      const targetIndex = Math.max(tiers.indexOf(record.target_tier), currentIndex);
      const nextIndex = Math.min(currentIndex + 1, targetIndex);
      record.current_tier = tiers[nextIndex];
      record.status = record.current_tier === record.target_tier ? "completed" : "active";
      record.next_tier = nextIndex >= targetIndex ? null : tiers[nextIndex + 1] ?? null;
      record.completed_at = record.status === "completed" ? timestamp : null;
    } else if (action === "hold") {
      record.status = "held";
    } else {
      record.status = "rolled_back";
      record.rollback_target = record.champion;
      record.completed_at = timestamp;
      record.next_tier = null;
    }
    record.updated_at = timestamp;
    record.updated_by = actor;
    promotionState.events.unshift({
      event: `promotion_${action}`,
      promotion_id: record.id,
      role_id: record.role_id,
      candidate: record.candidate,
      tier: record.current_tier,
      status: record.status,
      timestamp,
      actor,
    });
    return { promotion: record };
  }

  if (method === "POST" && basePath === "/v1/models/governance/retirements") {
    const assetClass = typeof payload?.asset_class === "string" ? payload.asset_class : "models";
    const assetId =
      typeof payload?.asset_id === "string" ? payload.asset_id : "frontier_supervisor:Claude";
    const label =
      typeof payload?.label === "string" ? payload.label : "Frontier supervisor champion Claude";
    const targetStage =
      typeof payload?.target_stage === "string" ? payload.target_stage : "retired_reference_only";
    const actor = typeof payload?.actor === "string" ? payload.actor : "fixture-operator";
    const existing = retirementState.records.find(
      (record) => record.asset_class === assetClass && record.asset_id === assetId && record.status !== "rolled_back"
    );
    if (existing) {
      return { retirement: existing };
    }
    const record: FixtureRetirementRecord = {
      id: `retirement-${assetClass}-${assetId}`.toLowerCase().replace(/[^a-z0-9-]/g, "-"),
      asset_class: assetClass,
      asset_id: assetId,
      label,
      current_stage: "active",
      target_stage: targetStage,
      status: "staged",
      reason:
        typeof payload?.reason === "string" && payload.reason
          ? payload.reason
          : `Fixture staged ${label} for governed retirement.`,
      created_at: timestamp,
      updated_at: timestamp,
      updated_by: actor,
      source: "dashboard_model_governance",
      next_stage: "deprecated",
      completed_at: null,
      rollback_target: "active",
      notes: ["Fixture governed retirement created from the cockpit."],
    };
    retirementState.records.unshift(record);
    retirementState.events.unshift({
      event: "retirement_staged",
      retirement_id: record.id,
      asset_class: record.asset_class,
      asset_id: record.asset_id,
      target_stage: record.target_stage,
      timestamp,
      actor,
    });
    return { retirement: record };
  }

  if (method === "POST" && /\/v1\/models\/governance\/retirements\/[^/]+\/(advance|hold|rollback)$/.test(basePath)) {
    const action = basePath.split("/").at(-1) ?? "advance";
    const retirementId = basePath.split("/").at(-2) ?? "";
    const actor = typeof payload?.actor === "string" ? payload.actor : "fixture-operator";
    const record = retirementState.records.find((entry) => entry.id === retirementId);
    if (!record) {
      return { error: `Retirement ${retirementId} not found.`, status: 404 };
    }
    if (action === "advance") {
      const stages = ["active", "deprecated", "retired_reference_only"];
      const currentIndex = Math.max(stages.indexOf(record.current_stage), 0);
      const targetIndex = Math.max(stages.indexOf(record.target_stage), currentIndex);
      const nextIndex = Math.min(currentIndex + 1, targetIndex);
      record.current_stage = stages[nextIndex];
      record.status = record.current_stage === record.target_stage ? "completed" : "active";
      record.next_stage = nextIndex >= targetIndex ? null : stages[nextIndex + 1] ?? null;
      record.completed_at = record.status === "completed" ? timestamp : null;
    } else if (action === "hold") {
      record.status = "held";
    } else {
      record.status = "rolled_back";
      record.current_stage = "active";
      record.rollback_target = "active";
      record.completed_at = timestamp;
      record.next_stage = null;
    }
    record.updated_at = timestamp;
    record.updated_by = actor;
    retirementState.events.unshift({
      event: `retirement_${action}`,
      retirement_id: record.id,
      asset_class: record.asset_class,
      asset_id: record.asset_id,
      stage: record.current_stage,
      status: record.status,
      timestamp,
      actor,
    });
    return { retirement: record };
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
    const fixtureResponse = await buildFixtureAgentResponse(path, init);
    if (fixtureResponse) {
      const response = NextResponse.json(fixtureResponse);
      if (path === "/v1/governor" || path.startsWith("/v1/governor/")) {
        response.cookies.set(
          FIXTURE_GOVERNOR_STATE_COOKIE,
          serializeFixtureGovernorState(await getFixtureGovernorState()),
          {
            path: "/",
            httpOnly: true,
            sameSite: "lax",
          }
        );
      }
      return response;
    }
  }

  try {
    const response = await fetch(joinUrl(config.agentServer.url, path), {
      ...init,
      headers: { ...agentServerHeaders(), ...init?.headers },
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
