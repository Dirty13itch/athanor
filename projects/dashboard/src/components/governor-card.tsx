"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PauseCircle, PlayCircle, ShieldCheck } from "lucide-react";
import { requestJson } from "@/features/workforce/helpers";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getGovernor } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

function formatWindowLabel(value: string) {
  return value
    .split(/[-_]/g)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function badgeVariant(value: string) {
  if (value === "degraded" || value === "paused") {
    return "destructive" as const;
  }
  if (value === "constrained") {
    return "secondary" as const;
  }
  return "outline" as const;
}

export function GovernorCard({
  title = "Governor posture",
  description = "Automation lanes, capacity pressure, and direct pause or resume control for the runtime commander.",
  compact = false,
}: {
  title?: string;
  description?: string;
  compact?: boolean;
}) {
  const governorQuery = useQuery({
    queryKey: queryKeys.governor,
    queryFn: getGovernor,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
  const [busyScope, setBusyScope] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  async function toggleScope(scope: string, paused: boolean) {
    setBusyScope(scope);
    setFeedback(null);
    try {
      await requestJson(paused ? "/api/governor/resume" : "/api/governor/pause", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scope,
          actor: "dashboard-operator",
          reason: paused ? "" : `Paused from cockpit (${scope})`,
        }),
      });
      await governorQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Governor request failed.");
    } finally {
      setBusyScope(null);
    }
  }

  async function updatePresence(state: string) {
    setBusyScope(`presence:${state}`);
    setFeedback(null);
    try {
      await requestJson("/api/governor/presence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          state,
          mode: "manual",
          actor: "dashboard-operator",
          reason: `Presence set from cockpit (${state})`,
        }),
      });
      await governorQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Presence update failed.");
    } finally {
      setBusyScope(null);
    }
  }

  async function enableAutomaticPresence() {
    const inferredState =
      typeof document !== "undefined" && document.hidden ? "away" : "at_desk";
    setBusyScope("presence:auto");
    setFeedback(null);
    try {
      await requestJson("/api/governor/presence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          state: inferredState,
          mode: "auto",
          actor: "dashboard-operator",
          reason: "Returned presence posture to automatic dashboard heartbeat.",
        }),
      });
      await governorQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Automatic presence update failed.");
    } finally {
      setBusyScope(null);
    }
  }

  async function updateReleaseTier(tier: string) {
    setBusyScope(`tier:${tier}`);
    setFeedback(null);
    try {
      await requestJson("/api/governor/release-tier", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tier,
          actor: "dashboard-operator",
          reason: `Release tier set from cockpit (${tier})`,
        }),
      });
      await governorQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Release-tier update failed.");
    } finally {
      setBusyScope(null);
    }
  }

  if (governorQuery.isError && !governorQuery.data) {
    return (
      <ErrorPanel
        title={title}
        description={
          governorQuery.error instanceof Error
            ? governorQuery.error.message
            : "Failed to load governor state."
        }
      />
    );
  }

  const snapshot = governorQuery.data;
  if (!snapshot) {
    return (
      <EmptyState
        title="No governor state yet"
        description="The runtime governor has not returned a posture snapshot."
      />
    );
  }

  const activeLaneCount = snapshot.lanes.filter((lane) => !lane.paused).length;
  const pausedLaneCount = snapshot.lanes.length - activeLaneCount;
  const actionableLanes = compact
    ? snapshot.lanes.filter((lane) =>
        ["scheduler", "research_jobs", "benchmark_cycle"].includes(lane.id)
      )
    : snapshot.lanes;

  return (
    <Card className="surface-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <ShieldCheck className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {feedback ? (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-100 shadow-[0_16px_34px_-28px_rgb(127_29_29/0.9)]">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-4">
          <Metric label="Global mode" value={formatLabel(snapshot.global_mode)} />
          <Metric label="Capacity" value={formatLabel(snapshot.capacity.posture)} />
          <Metric label="Active lanes" value={`${activeLaneCount}`} />
          <Metric label="Paused lanes" value={`${pausedLaneCount}`} />
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            variant={snapshot.global_mode === "paused" ? "default" : "outline"}
            onClick={() => void toggleScope("global", snapshot.global_mode === "paused")}
            disabled={busyScope !== null}
          >
            {snapshot.global_mode === "paused" ? (
              <PlayCircle className="mr-2 h-4 w-4" />
            ) : (
              <PauseCircle className="mr-2 h-4 w-4" />
            )}
            {snapshot.global_mode === "paused" ? "Resume all automation" : "Pause all automation"}
          </Button>
          <Badge variant={badgeVariant(snapshot.degraded_mode)}>
            degraded mode {formatLabel(snapshot.degraded_mode)}
          </Badge>
          <Badge variant="outline">rights {snapshot.command_rights_version}</Badge>
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Lane controls
            </p>
            <div className="grid gap-2">
              {actionableLanes.map((lane) => (
                <div key={lane.id} className="surface-metric rounded-xl border px-3 py-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-medium">{lane.label}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{lane.description}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={badgeVariant(lane.status)}>{formatLabel(lane.status)}</Badge>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void toggleScope(lane.id, lane.paused)}
                        disabled={busyScope !== null}
                      >
                        {lane.paused ? "Resume" : "Pause"}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Operator presence
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant={snapshot.presence.mode === "auto" ? "default" : "outline"}
                  onClick={() => void enableAutomaticPresence()}
                  disabled={busyScope !== null}
                >
                  Auto
                </Button>
                {["at_desk", "away", "asleep", "phone_only"].map((state) => {
                  const selected =
                    snapshot.presence.mode === "manual" &&
                    snapshot.presence.configured_state === state;
                  return (
                    <Button
                      key={state}
                      size="sm"
                      variant={selected ? "default" : "outline"}
                      onClick={() => void updatePresence(state)}
                      disabled={busyScope !== null}
                    >
                      {formatLabel(state)}
                    </Button>
                  );
                })}
              </div>
              <div className="mt-3 space-y-1 text-xs text-muted-foreground">
                <p>effective {snapshot.presence.label}</p>
                <p>
                  mode {snapshot.presence.mode} | configured {snapshot.presence.configured_label}
                </p>
                <p>automation {snapshot.presence.automation_posture}</p>
                <p>notifications {snapshot.presence.notification_posture}</p>
                <p>approvals {snapshot.presence.approval_posture}</p>
                {snapshot.presence.signal_source ? (
                  <p>
                    signal {snapshot.presence.signal_fresh ? "fresh" : "stale"} via{" "}
                    {formatLabel(snapshot.presence.signal_source)}
                    {snapshot.presence.signal_age_seconds !== null
                      ? ` (${Math.round(snapshot.presence.signal_age_seconds)}s ago)`
                      : ""}
                  </p>
                ) : null}
                <p>{snapshot.presence.effective_reason}</p>
              </div>
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Promotion tier
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {snapshot.release_tier.available_tiers.map((tier) => {
                  const selected = snapshot.release_tier.state === tier;
                  return (
                    <Button
                      key={tier}
                      size="sm"
                      variant={selected ? "default" : "outline"}
                      onClick={() => void updateReleaseTier(tier)}
                      disabled={busyScope !== null}
                    >
                      {formatLabel(tier)}
                    </Button>
                  );
                })}
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                current tier {formatLabel(snapshot.release_tier.state)}
              </p>
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Capacity posture
              </p>
              <div className="mt-2 grid gap-2 text-sm text-muted-foreground">
                <span>
                  queue {snapshot.capacity.queue.posture} | {snapshot.capacity.queue.running}/
                  {snapshot.capacity.queue.max_concurrent} running
                </span>
                <span>
                  scheduler {snapshot.capacity.scheduler.running ? "running" : "stopped"} |{" "}
                  {snapshot.capacity.scheduler.enabled_count} enabled jobs
                </span>
                <span>
                  provider reserve {snapshot.capacity.provider_reserve.posture} |{" "}
                  {snapshot.capacity.provider_reserve.constrained_count} constrained
                </span>
                <span>
                  workspace utilization{" "}
                  {Math.round(snapshot.capacity.workspace.utilization * 100)}%
                </span>
                <span>
                  active windows {snapshot.capacity.active_time_windows.length}
                </span>
              </div>
              {snapshot.capacity.active_time_windows.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {snapshot.capacity.active_time_windows.map((window) => (
                    <Badge key={window.id} variant="outline">
                      {formatWindowLabel(window.id)} | {window.window}
                    </Badge>
                  ))}
                </div>
              ) : null}
            </div>

            <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Node posture
              </p>
              <div className="mt-2 space-y-2">
                {snapshot.capacity.nodes.slice(0, compact ? 2 : 4).map((node) => (
                  <div key={node.id} className="flex items-center justify-between gap-3 text-sm">
                    <div>
                      <p className="font-medium">{node.id}</p>
                      <p className="text-xs text-muted-foreground">
                        {node.healthy_models}/{node.total_models} models healthy
                      </p>
                    </div>
                    <Badge variant={badgeVariant(node.stale || !node.alive ? "degraded" : "live")}>
                      {node.stale || !node.alive
                        ? "degraded"
                        : `${Math.round(node.max_gpu_util_pct)}% gpu`}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="surface-metric rounded-xl border px-3 py-3">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
            Governor recommendations
          </p>
          <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
            {snapshot.capacity.recommendations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          {snapshot.capacity.active_time_windows.length ? (
            <p className="mt-3 text-xs text-muted-foreground">
              protected windows{" "}
              {snapshot.capacity.active_time_windows
                .map((window) => formatWindowLabel(window.id))
                .join(", ")}
            </p>
          ) : null}
          <p className="mt-3 text-xs text-muted-foreground" data-volatile="true">
            updated {formatRelativeTime(snapshot.updated_at ?? snapshot.generated_at)}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-metric rounded-xl border px-3 py-3">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
