"use client";

import { useQuery } from "@tanstack/react-query";
import { RefreshCcw, ShieldCheck, Layers, Radio, Gauge } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { GovernorCard } from "@/components/governor-card";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { getGovernor } from "@/lib/api";
import { type GovernorSnapshot } from "@/lib/contracts";
import { formatRelativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { requestJson } from "@/features/workforce/helpers";

interface TrustScore {
  agent_id: string;
  agent_name: string;
  score: number;
  level: string;
}

function trustBadgeVariant(level: string) {
  const l = level.toLowerCase();
  if (l === "high" || l === "full" || l === "a" || l === "a+") return "outline" as const;
  if (l === "medium" || l === "standard" || l === "b" || l === "b+") return "secondary" as const;
  return "destructive" as const;
}

function trustBarColor(score: number) {
  if (score >= 0.8) return "bg-[color:var(--signal-success)]";
  if (score >= 0.5) return "bg-[color:var(--signal-warning)]";
  return "bg-[color:var(--signal-danger)]";
}

function controlStackStatusClass(status: string) {
  if (status === "active" || status === "ok" || status === "healthy" || status === "live") return "text-[color:var(--signal-success)]";
  if (status === "degraded" || status === "warning") return "text-[color:var(--signal-warning)]";
  if (status === "failed" || status === "error") return "text-[color:var(--signal-danger)]";
  return "text-muted-foreground";
}

export function GovernorConsole() {
  const governorQuery = useQuery({
    queryKey: queryKeys.governor,
    queryFn: getGovernor,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const trustQuery = useQuery({
    queryKey: ["trust-scores"],
    queryFn: async (): Promise<TrustScore[]> => {
      const data = await requestJson("/api/agents/proxy?path=/v1/trust");
      // Agent Server returns { agents: { agent_id: { score, grade, ... } } }
      const agents = data?.agents;
      if (agents && typeof agents === "object" && !Array.isArray(agents)) {
        return Object.entries(agents).map(([id, entry]: [string, any]) => ({
          agent_id: id,
          agent_name: id.replace(/-/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
          score: entry.score ?? 0,
          level: entry.grade ?? "unknown",
        }));
      }
      // Fallback for legacy array format
      return (data?.scores ?? data ?? []) as TrustScore[];
    },
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  if (governorQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Workforce"
          title="Governor"
          description="The governor snapshot failed to load."
          attentionHref="/governor"
        />
        <ErrorPanel
          description={
            governorQuery.error instanceof Error
              ? governorQuery.error.message
              : "Failed to load governor data."
          }
        />
      </div>
    );
  }

  const snapshot = governorQuery.data;
  const trustScores = trustQuery.data ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workforce"
        title="Governor"
        description="Runtime control plane — lanes, capacity, presence, and autonomy levels."
        attentionHref="/governor"
        actions={
          <Button
            variant="outline"
            onClick={() => void governorQuery.refetch()}
            disabled={governorQuery.isFetching}
          >
            <RefreshCcw className={`mr-2 h-4 w-4 ${governorQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        {snapshot ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Global Mode"
              value={snapshot.global_mode}
              detail={snapshot.reason}
              icon={<ShieldCheck className="h-5 w-5" />}
              tone={snapshot.global_mode === "active" ? "success" : "warning"}
            />
            <StatCard
              label="Lanes"
              value={`${snapshot.lanes.length}`}
              detail={`${snapshot.lanes.filter((l) => l.status === "active").length} active, ${snapshot.lanes.filter((l) => l.status === "paused").length} paused`}
              icon={<Layers className="h-5 w-5" />}
            />
            <StatCard
              label="Presence"
              value={snapshot.presence.label}
              detail={snapshot.presence.effective_reason}
              icon={<Radio className="h-5 w-5" />}
              tone={snapshot.presence.state === "at_desk" || snapshot.presence.state === "active" ? "success" : "warning"}
            />
            <StatCard
              label="Release Tier"
              value={snapshot.release_tier.state}
              detail={`Updated by ${snapshot.release_tier.updated_by}`}
              icon={<Gauge className="h-5 w-5" />}
            />
          </div>
        ) : null}
      </PageHeader>

      <GovernorCard
        title="Governor posture"
        description="Automation lanes, capacity pressure, and direct pause or resume control for the runtime commander."
        compact={false}
      />

      {/* Control Stack / Decision Audit */}
      {snapshot ? (
        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Control Stack</CardTitle>
            <CardDescription>
              Active governor decision layers and their current status.
              {snapshot.updated_at ? ` Last updated ${formatRelativeTime(snapshot.updated_at)}.` : ""}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {snapshot.control_stack.length > 0 ? (
              <div className="space-y-2">
                {snapshot.control_stack.map((entry) => (
                  <div
                    key={entry.id}
                    className="surface-instrument flex items-center justify-between rounded-xl border px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium">{entry.label}</span>
                      <span className="text-xs text-muted-foreground">{entry.id}</span>
                    </div>
                    <span className={`text-sm font-medium ${controlStackStatusClass(entry.status)}`}>
                      {entry.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No control stack entries"
                description="The governor control stack is empty."
                className="py-8"
              />
            )}
          </CardContent>
        </Card>
      ) : null}

      {/* Trust Scores */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Agent Trust Scores</CardTitle>
          <CardDescription>Per-agent trust levels as evaluated by the governor.</CardDescription>
        </CardHeader>
        <CardContent>
          {trustQuery.isError ? (
            <p className="text-sm text-muted-foreground">Trust scores unavailable.</p>
          ) : trustScores.length > 0 ? (
            <div className="space-y-3">
              {trustScores.map((entry) => (
                <div key={entry.agent_id} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{entry.agent_name}</span>
                      <Badge variant={trustBadgeVariant(entry.level)}>{entry.level}</Badge>
                    </div>
                    <span className="text-sm tabular-nums text-muted-foreground">
                      {(entry.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-border/50">
                    <div
                      className={`h-1.5 rounded-full transition-all ${trustBarColor(entry.score)}`}
                      style={{ width: `${Math.min(entry.score * 100, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No trust scores available"
              description="Trust scores will appear once agents have been evaluated."
              className="py-8"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
