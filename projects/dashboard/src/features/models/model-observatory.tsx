"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { RefreshCcw, Cpu, Server, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusDot } from "@/components/status-dot";
import { getGpuSnapshot, getModelGovernance } from "@/lib/api";
import { type GpuSnapshotResponse } from "@/lib/contracts";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";
import { queryKeys } from "@/lib/query-client";
import { requestJson } from "@/features/workforce/helpers";

// Model definitions (from server props)

interface LocalModelDef {
  alias: string;
  litellmAlias: string;
  name: string;
  node: string;
  nodeId: string;
  description: string;
}

export interface ModelObservatoryProps {
  localModels: LocalModelDef[];
}

// Assignment matrix

type AssignmentKind = "primary" | "fallback";

const ASSIGNMENTS: Record<string, Record<string, AssignmentKind>> = {
  "general-assistant": { reasoning: "primary" },
  "research-agent": { reasoning: "primary", gemini: "fallback" },
  "coding-agent": { coder: "primary", codex: "fallback", gemini: "fallback" },
  "creative-agent": { fast: "primary" },
  "knowledge-agent": { reasoning: "primary" },
  "home-agent": { reasoning: "primary" },
  "media-agent": { fast: "primary", gemini: "fallback" },
  "stash-agent": { fast: "primary" },
  "data-curator": { fast: "primary", embedding: "primary", aider: "fallback" },
};

const AGENT_DISPLAY: Record<string, string> = {
  "general-assistant": "General Assistant",
  "research-agent": "Research",
  "coding-agent": "Coding",
  "creative-agent": "Creative",
  "knowledge-agent": "Knowledge",
  "home-agent": "Home",
  "media-agent": "Media",
  "stash-agent": "Stash",
  "data-curator": "Data Curator",
};

const MATRIX_COLUMNS = [
  "reasoning",
  "fast",
  "coder",
  "embedding",
  "claude",
  "codex",
  "gemini",
  "aider",
];

// Live data types

interface RoutingLogEntry {
  task_id?: string;
  provider?: string;
  policy_class?: string;
  outcome?: string;
  timestamp?: string;
}

// Helper functions

function vramForModel(
  model: LocalModelDef,
  snapshot: GpuSnapshotResponse | undefined
): { usedMiB: number | null; totalMiB: number | null } {
  if (!snapshot) return { usedMiB: null, totalMiB: null };

  const nodeGpus = snapshot.gpus.filter(
    (g) => g.node.toLowerCase() === model.nodeId.toLowerCase()
  );
  if (nodeGpus.length === 0) return { usedMiB: null, totalMiB: null };

  // Match GPUs by alias (config backend IDs) or model name heuristics
  let gpus = nodeGpus;
  if (model.alias === "foundry-coordinator") {
    gpus = nodeGpus.filter((g) => !g.gpuName.includes("4090"));
  } else if (model.alias === "foundry-coder") {
    gpus = nodeGpus.filter((g) => g.gpuName.includes("4090"));
  } else if (model.alias === "dev-embedding" || model.alias === "dev-reranker") {
    gpus = nodeGpus.filter((g) => g.gpuName.includes("5060"));
  }

  if (gpus.length === 0) gpus = nodeGpus.slice(0, 1);

  const usedMiB = gpus.reduce((s, g) => s + (g.memoryUsedMiB ?? 0), 0);
  const totalMiB = gpus.reduce((s, g) => s + (g.memoryTotalMiB ?? 0), 0);
  return { usedMiB, totalMiB };
}

function gbFromMiB(mib: number | null): string {
  if (mib === null) return "--";
  return `${(mib / 1024).toFixed(1)} GB`;
}

function vramPct(usedMiB: number | null, totalMiB: number | null): number {
  if (!usedMiB || !totalMiB || totalMiB === 0) return 0;
  return Math.min((usedMiB / totalMiB) * 100, 100);
}

function vramBarColor(pct: number): string {
  if (pct >= 90) return "bg-[color:var(--signal-danger)]";
  if (pct >= 70) return "bg-[color:var(--signal-warning)]";
  return "bg-[color:var(--signal-success)]";
}

function policyClass(entry: RoutingLogEntry): string {
  return entry.policy_class ?? "local_only";
}

function capabilityLabel(value: string | null | undefined): string {
  return String(value ?? "unknown").replace(/[_-]/g, " ");
}

// Main component

export function ModelObservatory({ localModels }: ModelObservatoryProps) {
  const operatorSession = useOperatorSessionStatus();
  const routingReadEnabled = !operatorSession.isPending && !isOperatorSessionLocked(operatorSession);
  const gpuQuery = useQuery({
    queryKey: queryKeys.gpuSnapshot,
    queryFn: getGpuSnapshot,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });

  const routingQuery = useQuery({
    queryKey: ["routing-log-models"],
    queryFn: async (): Promise<RoutingLogEntry[]> => {
      const data = await requestJson(
        "/api/routing/log?limit=20"
      );
      return (data?.entries ?? data ?? []) as RoutingLogEntry[];
    },
    enabled: routingReadEnabled,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const capabilityQuery = useQuery({
    queryKey: queryKeys.modelGovernance,
    queryFn: getModelGovernance,
    enabled: routingReadEnabled,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const snapshot = gpuQuery.data;
  const routingEntries = routingQuery.data ?? [];
  const capabilityIntelligence = capabilityQuery.data?.capability_intelligence ?? null;

  const isFetching = gpuQuery.isFetching || routingQuery.isFetching || capabilityQuery.isFetching;

  // Routing split
  const total = routingEntries.length;
  const localCount = routingEntries.filter(
    (e) => policyClass(e) === "local_only"
  ).length;
  const cliReviewCount = routingEntries.filter(
    (e) => policyClass(e) === "cli_review"
  ).length;
  const cliExecCount = routingEntries.filter(
    (e) => policyClass(e) === "cli_execution"
  ).length;

  const localPct = total > 0 ? (localCount / total) * 100 : 0;
  const cliReviewPct = total > 0 ? (cliReviewCount / total) * 100 : 0;
  const cliExecPct = total > 0 ? (cliExecCount / total) * 100 : 0;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Intelligence"
        title="Model Observatory"
        description="Local inference fleet, routing split, and agent-to-model assignments. Provider economics now live in Subscriptions."
        attentionHref="/models"
        actions={
          <>
            <Button asChild variant="outline">
              <Link href="/subscriptions">Open Subscriptions</Link>
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                void gpuQuery.refetch();
                void routingQuery.refetch();
              }}
              disabled={isFetching}
            >
              <RefreshCcw
                className={`mr-2 h-4 w-4 ${isFetching ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <StatCard
            label="Local Models"
            value={`${localModels.length}`}
            detail="Always-on, $0/token"
            icon={<Cpu className="h-5 w-5" />}
            tone="success"
          />
          <StatCard
            label="Provider Economics"
            value="Subscriptions"
            detail="Open burn, leases, and handoffs."
            icon={<Server className="h-5 w-5" />}
          />
          <StatCard
            label="Local Execution"
            value={total > 0 ? `${localPct.toFixed(0)}%` : "--"}
            detail={total > 0 ? `${localCount} of ${total} recent` : "No routing data"}
            icon={<Zap className="h-5 w-5" />}
            tone={localPct >= 80 ? "success" : "default"}
          />
        </div>
      </PageHeader>

      {/* Section 1 - Local Models */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Local Models</CardTitle>
          <CardDescription>
            Always-on inference fleet. Zero per-token cost. Live VRAM from Prometheus.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 lg:grid-cols-2">
            {localModels.map((model) => {
              const { usedMiB, totalMiB } = vramForModel(model, snapshot);
              const pct = vramPct(usedMiB, totalMiB);
              const agentNames = Object.entries(ASSIGNMENTS)
                .filter(([, cols]) => cols[model.litellmAlias])
                .map(([agentId]) => AGENT_DISPLAY[agentId] ?? agentId);

              return (
                <div
                  key={model.alias}
                  className="surface-instrument flex flex-col gap-3 rounded-xl border px-4 py-4"
                >
                  {/* Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <StatusDot tone="healthy" pulse />
                        <span className="text-sm font-semibold">{model.name}</span>
                      </div>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        alias:{" "}
                        <span className="font-mono text-foreground">
                          {model.litellmAlias}
                        </span>
                      </p>
                    </div>
                    <Badge variant="outline" className="shrink-0 text-xs">
                      {model.node}
                    </Badge>
                  </div>

                  {/* Description */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="truncate">{model.description}</span>
                    <span className="font-mono tabular-nums shrink-0 ml-2">
                      SERVING
                    </span>
                  </div>

                  {/* VRAM bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>VRAM</span>
                      <span className="tabular-nums">
                        {gbFromMiB(usedMiB)} / {gbFromMiB(totalMiB)}
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-border/50">
                      <div
                        className={`h-1.5 rounded-full transition-all ${vramBarColor(pct)}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>

                  {/* Agents using this model */}
                  {agentNames.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {agentNames.map((name) => (
                        <Badge key={name} variant="secondary" className="text-xs">
                          {name}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Capability leaders</CardTitle>
          <CardDescription>
            Live routing leaders from model governance. Spend still lives in Subscriptions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {capabilityIntelligence ? (
            <div className="grid gap-3 lg:grid-cols-4">
              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Implementation</p>
                <p className="mt-2 text-sm font-semibold">
                  {capabilityIntelligence.implementation
                    ? `${capabilityLabel(capabilityIntelligence.implementation.subject_id)} (${capabilityIntelligence.implementation.capability_score})`
                    : "none"}
                </p>
              </div>
              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Audit</p>
                <p className="mt-2 text-sm font-semibold">
                  {capabilityIntelligence.audit
                    ? `${capabilityLabel(capabilityIntelligence.audit.subject_id)} (${capabilityIntelligence.audit.capability_score})`
                    : "none"}
                </p>
              </div>
              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Local endpoint</p>
                <p className="mt-2 text-sm font-semibold">
                  {capabilityIntelligence.local_endpoint
                    ? `${capabilityLabel(capabilityIntelligence.local_endpoint.subject_id)} (${capabilityIntelligence.local_endpoint.capability_score})`
                    : "none"}
                </p>
              </div>
              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Degraded</p>
                <p className="mt-2 text-sm font-semibold">{capabilityIntelligence.degraded_subject_count}</p>
                <p className="mt-1 text-xs text-muted-foreground">{capabilityIntelligence.source_of_truth}</p>
              </div>
            </div>
          ) : (
            <EmptyState
              title="No capability snapshot yet"
              description="Capability leaders will appear here once model governance exposes the shared capability posture."
              className="py-8"
            />
          )}
        </CardContent>
      </Card>

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Provider economics</CardTitle>
          <CardDescription>
            Burn, leases, and handoffs live in Subscriptions. This page keeps the model and routing view focused.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="surface-instrument flex flex-wrap items-center justify-between gap-3 rounded-2xl border px-4 py-4">
            <p className="text-sm text-muted-foreground">
              Open the canonical home for provider spend, lease tracking, and execution history.
            </p>
            <Button asChild variant="outline">
              <Link href="/subscriptions">Open Subscriptions</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Section 2 - Routing Intelligence */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Routing Intelligence</CardTitle>
          <CardDescription>
            Today&apos;s execution split and recent routing decisions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Stacked bar */}
          {total > 0 ? (
            <div className="space-y-2">
              <div className="flex h-6 w-full overflow-hidden rounded-full bg-border/40">
                {localPct > 0 && (
                  <div
                    className="flex items-center justify-center bg-[color:var(--signal-success)] text-[10px] font-semibold text-black/80 transition-all"
                    style={{ width: `${localPct}%` }}
                    title={`Local: ${localPct.toFixed(0)}%`}
                  >
                    {localPct >= 12 ? `${localPct.toFixed(0)}%` : ""}
                  </div>
                )}
                {cliReviewPct > 0 && (
                  <div
                    className="flex items-center justify-center bg-[color:var(--signal-warning)] text-[10px] font-semibold text-black/80 transition-all"
                    style={{ width: `${cliReviewPct}%` }}
                    title={`CLI Review: ${cliReviewPct.toFixed(0)}%`}
                  >
                    {cliReviewPct >= 12 ? `${cliReviewPct.toFixed(0)}%` : ""}
                  </div>
                )}
                {cliExecPct > 0 && (
                  <div
                    className="flex items-center justify-center bg-[color:var(--signal-info)] text-[10px] font-semibold text-black/80 transition-all"
                    style={{ width: `${cliExecPct}%` }}
                    title={`CLI Exec: ${cliExecPct.toFixed(0)}%`}
                  >
                    {cliExecPct >= 12 ? `${cliExecPct.toFixed(0)}%` : ""}
                  </div>
                )}
              </div>
              <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-2 w-2 rounded-full bg-[color:var(--signal-success)]" />
                  Local execution {localPct.toFixed(0)}%
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-2 w-2 rounded-full bg-[color:var(--signal-warning)]" />
                  CLI review {cliReviewPct.toFixed(0)}%
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-2 w-2 rounded-full bg-[color:var(--signal-info)]" />
                  CLI execution {cliExecPct.toFixed(0)}%
                </span>
              </div>
            </div>
          ) : (
            <div className="h-6 w-full rounded-full bg-border/40" />
          )}

          {/* Recent routing log */}
          {routingEntries.length > 0 ? (
            <div className="space-y-1">
              <div className="surface-tile grid grid-cols-4 gap-2 rounded-xl px-4 py-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <span>Task</span>
                <span>Policy</span>
                <span>Provider</span>
                <span className="text-right">Outcome</span>
              </div>
              {routingEntries.slice(0, 15).map((entry, idx) => (
                <div
                  key={entry.task_id ?? idx}
                  className="surface-tile grid grid-cols-4 items-center gap-2 rounded-xl px-4 py-2"
                >
                  <span className="truncate font-mono text-xs text-muted-foreground">
                    {entry.task_id
                      ? entry.task_id.length > 12
                        ? `${entry.task_id.slice(0, 12)}...`
                        : entry.task_id
                      : "--"}
                  </span>
                  <span className="text-sm">
                    {entry.policy_class ?? "--"}
                  </span>
                  <span className="text-sm">{entry.provider ?? "--"}</span>
                  <span className="text-right">
                    <Badge
                      variant={
                        entry.outcome === "success"
                          ? "outline"
                          : entry.outcome === "fail" || entry.outcome === "failed"
                          ? "destructive"
                          : "default"
                      }
                    >
                      {entry.outcome ?? "pending"}
                    </Badge>
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No routing data"
              description="Routing decisions will appear as tasks are classified and dispatched."
              className="py-6"
            />
          )}
        </CardContent>
      </Card>

      {/* Section 4 - Assignment Matrix */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Agent Assignment Matrix</CardTitle>
          <CardDescription>
            Which models each agent uses. Filled = primary, faded = fallback.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="pb-3 pr-4 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Agent
                  </th>
                  {MATRIX_COLUMNS.map((col) => (
                    <th
                      key={col}
                      className="pb-3 px-2 text-center text-xs font-medium uppercase tracking-wider text-muted-foreground"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {Object.entries(ASSIGNMENTS).map(([agentId, cols]) => (
                  <tr key={agentId} className="group">
                    <td className="py-2.5 pr-4 text-sm font-medium text-foreground">
                      {AGENT_DISPLAY[agentId] ?? agentId}
                    </td>
                    {MATRIX_COLUMNS.map((col) => {
                      const kind = cols[col];
                      return (
                        <td key={col} className="py-2.5 px-2 text-center">
                          {kind === "primary" ? (
                            <span
                              className="inline-block h-4 w-4 rounded-sm bg-[color:var(--signal-success)] opacity-90"
                              title={`${col}: primary`}
                              aria-label={`${col}: primary`}
                            />
                          ) : kind === "fallback" ? (
                            <span
                              className="inline-block h-4 w-4 rounded-sm bg-[color:var(--signal-warning)] opacity-40"
                              title={`${col}: fallback`}
                              aria-label={`${col}: fallback`}
                            />
                          ) : (
                            <span
                              className="inline-block h-4 w-4 rounded-sm bg-border/20"
                              aria-hidden
                            />
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Legend */}
          <div className="mt-4 flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 rounded-sm bg-[color:var(--signal-success)] opacity-90" />
              Primary
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 rounded-sm bg-[color:var(--signal-warning)] opacity-40" />
              Fallback
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 rounded-sm bg-border/30" />
              Not assigned
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

