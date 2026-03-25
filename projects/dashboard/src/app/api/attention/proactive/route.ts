import { NextResponse } from "next/server";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AttentionItem {
  id: string;
  severity: "critical" | "warning" | "info";
  category: "capacity" | "quality" | "performance" | "security" | "cost";
  title: string;
  detail: string;
  action?: string;
  href?: string;
  source: string;
  timestamp: string;
}

interface ProactiveResponse {
  generated_at: string;
  total_items: number;
  severity_counts: { critical: number; warning: number; info: number };
  items: AttentionItem[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DEV = "http://192.168.1.189";
const FOUNDRY = "http://192.168.1.244";
const FETCH_TIMEOUT = 4_000;

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
    const res = await fetch(url, {
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(timer);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

function makeId(source: string, key: string): string {
  return `${source}:${key}`;
}

const SEVERITY_ORDER: Record<string, number> = { critical: 0, warning: 1, info: 2 };

// ---------------------------------------------------------------------------
// Source types (shaped from actual API responses)
// ---------------------------------------------------------------------------

interface BriefingItem {
  severity: string;
  category: string;
  message: string;
  action: string | null;
}
interface BriefingResponse {
  generated_at: string;
  items: BriefingItem[];
}

interface SentinelCheck {
  service: string;
  passed: boolean;
  latency_ms: number;
  detail: string;
  timestamp: number;
}
interface SentinelTier {
  total: number;
  passed: number;
  failed: number;
}
interface SentinelStatus {
  summary: {
    heartbeat: SentinelTier;
    readiness: SentinelTier;
    integration: SentinelTier;
  };
  tiers: {
    heartbeat: SentinelCheck[];
    readiness: SentinelCheck[];
    integration: SentinelCheck[];
  };
}

interface GovernorStats {
  total: number;
  queued: number;
  running: number;
  done: number;
  failed: number;
}

interface QualityGateStats {
  total_points: number;
  collections: Record<string, { points: number; vectors_count: number }>;
}

interface DiskPrediction {
  node: string;
  mount: string;
  current_pct: number;
  trend: string;
  trend_gb_per_day: number;
  days_to_full: number;
  alert: boolean;
  alert_message: string | null;
}
interface CapacityResponse {
  generated_at: string;
  disk_predictions: Record<string, DiskPrediction>;
  memory_leaks: Array<{ node: string; process: string; growth_mb_per_hour: number }>;
  gpu_thermal: Array<{ node: string; gpu: string; temp_c: number; threshold_c: number }>;
}

interface ImprovementProposal {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Aggregation logic
// ---------------------------------------------------------------------------

function processBriefing(data: BriefingResponse | null): AttentionItem[] {
  if (!data?.items?.length) return [];
  const now = data.generated_at ?? new Date().toISOString();
  return data.items.map((item, i) => ({
    id: makeId("brain-advisor", `${i}`),
    severity: (["critical", "warning", "info"].includes(item.severity)
      ? item.severity
      : "info") as AttentionItem["severity"],
    category: (["capacity", "quality", "performance", "security", "cost"].includes(item.category)
      ? item.category
      : "performance") as AttentionItem["category"],
    title: item.message,
    detail: item.action ?? "",
    action: item.action ?? undefined,
    href: "/services",
    source: "brain-advisor",
    timestamp: now,
  }));
}

function processSentinel(data: SentinelStatus | null): AttentionItem[] {
  if (!data) return [];
  const items: AttentionItem[] = [];
  const now = new Date().toISOString();

  for (const [tierName, checks] of Object.entries(data.tiers)) {
    for (const check of checks) {
      if (!check.passed) {
        items.push({
          id: makeId("sentinel", `${tierName}-${check.service}`),
          severity: "warning",
          category: "performance",
          title: `${check.service} failing ${tierName} check`,
          detail: check.detail,
          action: `Investigate ${check.service} \u2014 ${tierName} tier reports failure.`,
          href: "/services",
          source: "sentinel",
          timestamp: now,
        });
      }
    }
  }

  return items;
}

function processGovernor(data: GovernorStats | null): AttentionItem[] {
  if (!data) return [];
  const items: AttentionItem[] = [];
  const now = new Date().toISOString();
  const completed = data.done + data.failed;

  if (completed > 0) {
    const failureRate = data.failed / completed;
    if (failureRate > 0.5) {
      items.push({
        id: makeId("governor", "high-failure-rate"),
        severity: "warning",
        category: "performance",
        title: `Governor failure rate ${(failureRate * 100).toFixed(0)}%`,
        detail: `${data.failed} of ${completed} completed tasks failed. ${data.running} running, ${data.queued} queued.`,
        action: "Review failed tasks in the work planner for patterns.",
        href: "/workplanner",
        source: "governor",
        timestamp: now,
      });
    }
  }

  if (data.queued > 20) {
    items.push({
      id: makeId("governor", "queue-pressure"),
      severity: "info",
      category: "performance",
      title: `Governor queue backlog: ${data.queued} tasks queued`,
      detail: `${data.running} running, ${data.queued} waiting. Consider scaling agents or pausing intake.`,
      href: "/workplanner",
      source: "governor",
      timestamp: now,
    });
  }

  return items;
}

function processQualityGate(data: QualityGateStats | null): AttentionItem[] {
  if (!data) return [];
  const items: AttentionItem[] = [];
  const now = new Date().toISOString();

  if (data.total_points < 5000) {
    items.push({
      id: makeId("quality-gate", "low-data"),
      severity: "info",
      category: "quality",
      title: `Data volume low: ${data.total_points.toLocaleString()} total points`,
      detail: "Quality gate data is shrinking \u2014 check ingestion pipelines.",
      action: "Verify embedding and ingestion services are running.",
      href: "/services",
      source: "quality-gate",
      timestamp: now,
    });
  }

  // Flag large collections with zero vectors (embedding may be broken)
  for (const [name, col] of Object.entries(data.collections)) {
    if (col.points > 100 && col.vectors_count === 0) {
      items.push({
        id: makeId("quality-gate", `no-vectors-${name}`),
        severity: "info",
        category: "quality",
        title: `Collection "${name}" has ${col.points} points but 0 vectors`,
        detail: "Embeddings may not be generating for this collection.",
        action: `Check embedding pipeline for the ${name} collection.`,
        href: "/services",
        source: "quality-gate",
        timestamp: now,
      });
    }
  }

  return items;
}

function processCapacity(data: CapacityResponse | null): AttentionItem[] {
  if (!data) return [];
  const items: AttentionItem[] = [];
  const now = data.generated_at ?? new Date().toISOString();

  for (const pred of Object.values(data.disk_predictions)) {
    if (pred.days_to_full < 14) {
      items.push({
        id: makeId("brain-capacity", `disk-${pred.node}-${pred.mount}`),
        severity: "critical",
        category: "capacity",
        title: `${pred.node} ${pred.mount} fills in ${pred.days_to_full.toFixed(0)} days`,
        detail: `Currently ${pred.current_pct.toFixed(1)}% used, growing ${pred.trend_gb_per_day.toFixed(1)} GB/day.`,
        action: `Free space on ${pred.node} or expand the volume.`,
        href: "/services",
        source: "brain-capacity",
        timestamp: now,
      });
    } else if (pred.days_to_full < 30) {
      items.push({
        id: makeId("brain-capacity", `disk-${pred.node}-${pred.mount}`),
        severity: "warning",
        category: "capacity",
        title: `${pred.node} ${pred.mount} fills in ${pred.days_to_full.toFixed(0)} days`,
        detail: `Currently ${pred.current_pct.toFixed(1)}% used, growing ${pred.trend_gb_per_day.toFixed(1)} GB/day.`,
        action: `Plan capacity for ${pred.node}.`,
        href: "/services",
        source: "brain-capacity",
        timestamp: now,
      });
    }
  }

  for (const leak of data.memory_leaks) {
    items.push({
      id: makeId("brain-capacity", `memleak-${leak.node}-${leak.process}`),
      severity: "warning",
      category: "capacity",
      title: `Memory leak detected: ${leak.process} on ${leak.node}`,
      detail: `Growing at ${leak.growth_mb_per_hour.toFixed(1)} MB/hour.`,
      action: `Restart ${leak.process} on ${leak.node} and monitor.`,
      href: "/services",
      source: "brain-capacity",
      timestamp: new Date().toISOString(),
    });
  }

  for (const thermal of data.gpu_thermal) {
    items.push({
      id: makeId("brain-capacity", `thermal-${thermal.node}-${thermal.gpu}`),
      severity: "warning",
      category: "capacity",
      title: `GPU thermal alert: ${thermal.gpu} on ${thermal.node} at ${thermal.temp_c}\u00B0C`,
      detail: `Threshold is ${thermal.threshold_c}\u00B0C.`,
      action: `Check cooling on ${thermal.node} or reduce GPU workload.`,
      href: "/gpu",
      source: "brain-capacity",
      timestamp: new Date().toISOString(),
    });
  }

  return items;
}

function processProposals(data: ImprovementProposal[] | null): AttentionItem[] {
  if (!data?.length) return [];
  const unacted = data.filter((p) => p.status === "proposed" || p.status === "pending");
  if (unacted.length === 0) return [];

  return [
    {
      id: makeId("agent-server", "unacted-proposals"),
      severity: "info",
      category: "quality",
      title: `${unacted.length} improvement proposal${unacted.length > 1 ? "s" : ""} awaiting review`,
      detail: unacted.slice(0, 3).map((p) => p.title).join("; "),
      action: "Review proposals in the improvement dashboard.",
      href: "/improvement",
      source: "agent-server",
      timestamp: unacted[0]?.created_at ?? new Date().toISOString(),
    },
  ];
}

// ---------------------------------------------------------------------------
// Route handler
// ---------------------------------------------------------------------------

export async function GET() {
  const [briefing, sentinel, governor, qualityGate, capacity, proposals] =
    await Promise.all([
      fetchJson<BriefingResponse>(`${DEV}:8780/advisor/briefing`),
      fetchJson<SentinelStatus>(`${DEV}:8770/status`),
      fetchJson<GovernorStats>(`${DEV}:8760/stats`),
      fetchJson<QualityGateStats>(`${DEV}:8790/stats`),
      fetchJson<CapacityResponse>(`${DEV}:8780/capacity`),
      fetchJson<ImprovementProposal[]>(`${FOUNDRY}:9000/v1/improvement/proposals`),
    ]);

  const items: AttentionItem[] = [
    ...processBriefing(briefing),
    ...processSentinel(sentinel),
    ...processGovernor(governor),
    ...processQualityGate(qualityGate),
    ...processCapacity(capacity),
    ...processProposals(proposals),
  ].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);

  const counts = { critical: 0, warning: 0, info: 0 };
  for (const item of items) counts[item.severity]++;

  const response: ProactiveResponse = {
    generated_at: new Date().toISOString(),
    total_items: items.length,
    severity_counts: counts,
    items,
  };

  return NextResponse.json(response, {
    headers: { "Cache-Control": "s-maxage=30, stale-while-revalidate=60" },
  });
}
