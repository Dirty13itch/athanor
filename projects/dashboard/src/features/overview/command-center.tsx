"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Workflow,
} from "lucide-react";
import { ErrorPanel } from "@/components/error-panel";
import { StatusDot } from "@/components/status-dot";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { requestJson } from "@/features/workforce/helpers";
import { getOverview } from "@/lib/api";
import type { OverviewSnapshot } from "@/lib/contracts";
import { formatPercent, formatRelativeTime } from "@/lib/format";
import { LIVE_REFRESH_INTERVALS, liveQueryOptions } from "@/lib/live-updates";
import type { MasterAtlasRelationshipMap } from "@/lib/master-atlas";
import { queryKeys } from "@/lib/query-client";
import { cn } from "@/lib/utils";

type SignalTone = "healthy" | "warning" | "danger";

type TriageItem = {
  href: string;
  kicker: string;
  title: string;
  detail: string;
  metric: string;
  tone: SignalTone;
};

type RouteOwnershipItem = {
  href: string;
  label: string;
  description: string;
  metric?: string;
};

type WorkplanTaskPreview = NonNullable<
  OverviewSnapshot["workforce"]["workplan"]["current"]
>["tasks"][number];

type ProofDrilldownItem = {
  href: string;
  label: string;
  description: string;
};

function toneText(tone: SignalTone): string {
  if (tone === "danger") return "text-[color:var(--signal-danger)]";
  if (tone === "warning") return "text-[color:var(--signal-warning)]";
  return "text-[color:var(--signal-success)]";
}

function handoffTone(
  execution: MasterAtlasRelationshipMap["governed_dispatch_execution"] | null | undefined,
): SignalTone {
  if (!execution) return "warning";
  if (
    execution.resilience_state === "restart_interfering" ||
    execution.advisory_blockers?.includes("agent_runtime_restart_interfering")
  ) {
    return "danger";
  }
  if (execution.error) return "danger";
  if (execution.task_status === "running" || execution.backlog_status === "scheduled") return "healthy";
  if (
    execution.status === "already_dispatched" ||
    execution.status === "dispatched" ||
    execution.status === "claimed"
  ) {
    return "healthy";
  }
  if (execution.backlog_status === "waiting_approval" || execution.task_status === "pending_approval") {
    return "warning";
  }
  return "warning";
}

function MetricCell({
  label,
  value,
  detail,
  tone = "healthy",
}: {
  label: string;
  value: string;
  detail: string;
  tone?: SignalTone;
}) {
  return (
    <div className="flex min-h-[96px] flex-col justify-between px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
        <StatusDot tone={tone} pulse={tone !== "healthy"} />
      </div>
      <div className="space-y-1">
        <p className={cn("font-mono text-2xl font-semibold tracking-tight", toneText(tone))}>{value}</p>
        <p className="text-xs text-muted-foreground">{detail}</p>
      </div>
    </div>
  );
}

function TriageRow({ item }: { item: TriageItem }) {
  return (
    <Link
      href={item.href}
      className="group grid min-h-[72px] grid-cols-[auto_1fr_auto] items-center gap-4 border-b border-border/70 px-4 py-3 last:border-b-0 hover:bg-[color:var(--state-hover)]"
    >
      <StatusDot tone={item.tone} pulse={item.tone !== "healthy"} />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{item.kicker}</p>
          <p className={cn("text-xs font-semibold", toneText(item.tone))}>{item.metric}</p>
        </div>
        <p className="mt-1 text-sm font-medium text-foreground">{item.title}</p>
        <p className="mt-1 text-xs text-muted-foreground">{item.detail}</p>
      </div>
      <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground" />
    </Link>
  );
}

function SignalRow({
  href,
  kicker,
  title,
  detail,
  tone,
}: {
  href: string;
  kicker: string;
  title: string;
  detail: string;
  tone: SignalTone;
}) {
  return (
    <Link
      href={href}
      className="group grid min-h-[68px] grid-cols-[auto_1fr_auto] items-start gap-4 border-b border-border/70 px-4 py-3 last:border-b-0 hover:bg-[color:var(--state-hover)]"
    >
      <StatusDot tone={tone} pulse={tone !== "healthy"} className="mt-1" />
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{kicker}</p>
        <p className="mt-1 text-sm font-medium text-foreground">{title}</p>
        <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
      </div>
      <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground" />
    </Link>
  );
}

function NodeRow({ node }: { node: OverviewSnapshot["nodes"][number] }) {
  const tone: SignalTone =
    node.degradedServices > 0 ? "danger" : node.warningServices > 0 ? "warning" : "healthy";

  return (
    <Link
      href={`/services?node=${node.id}`}
      className="grid min-h-[76px] grid-cols-[1fr_auto] gap-4 border-b border-border/70 px-4 py-3 last:border-b-0 hover:bg-[color:var(--state-hover)]"
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <StatusDot tone={tone} pulse={tone !== "healthy"} />
          <p className="text-sm font-medium text-foreground">{node.name}</p>
          <span className="font-mono text-[11px] text-muted-foreground">{node.ip}</span>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {node.healthyServices}/{node.totalServices} services healthy, {node.warningServices} warning, {node.degradedServices} degraded
        </p>
      </div>
      <div className="text-right">
        <p className={cn("font-mono text-lg font-semibold tracking-tight", toneText(tone))}>
          {formatPercent(node.gpuUtilization, 0)}
        </p>
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">GPU avg</p>
      </div>
    </Link>
  );
}

function RouteOwnershipRow({ route }: { route: RouteOwnershipItem }) {
  return (
    <Link
      href={route.href}
      className="group grid min-h-[58px] grid-cols-[1fr_auto] items-center gap-4 border-b border-border/70 px-1 py-3 last:border-b-0 hover:bg-transparent"
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-foreground">{route.label}</p>
          {route.metric ? <p className="text-xs font-semibold text-primary">{route.metric}</p> : null}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{route.description}</p>
      </div>
      <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground" />
    </Link>
  );
}

function LiveReadoutRow({
  label,
  value,
  tone = "healthy",
}: {
  label: string;
  value: string;
  tone?: SignalTone;
}) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-border/70 bg-background/40 px-3 py-2.5">
      <StatusDot tone={tone} pulse={tone !== "healthy"} className="mt-1" />
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
        <p className={cn("mt-1 text-sm font-medium", toneText(tone))}>{value}</p>
      </div>
    </div>
  );
}

function ProofDrilldownRow({ item }: { item: ProofDrilldownItem }) {
  return (
    <Link
      href={item.href}
      className="group flex items-start justify-between gap-3 rounded-2xl border border-border/70 bg-background/40 px-3 py-2.5 transition-colors hover:bg-[color:var(--state-hover)]"
    >
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">{item.label}</p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.description}</p>
      </div>
      <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground" />
    </Link>
  );
}

function WorkplanTaskRow({ task }: { task: WorkplanTaskPreview }) {
  return (
    <div className="surface-instrument rounded-2xl border px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{task.priority}</Badge>
        {task.projectId ? <Badge variant="outline">{task.projectId}</Badge> : null}
        {task.requiresApproval ? <Badge variant="destructive">approval</Badge> : null}
      </div>
      <p className="mt-2 text-sm font-medium text-foreground">{task.prompt}</p>
      {task.rationale ? <p className="mt-1 text-xs leading-5 text-muted-foreground">{task.rationale}</p> : null}
    </div>
  );
}

export function CommandCenter({ initialSnapshot }: { initialSnapshot: OverviewSnapshot }) {
  const overviewQuery = useQuery({
    queryKey: queryKeys.overview,
    queryFn: getOverview,
    initialData: initialSnapshot,
    ...liveQueryOptions(LIVE_REFRESH_INTERVALS.overview),
  });
  const masterAtlasQuery = useQuery({
    queryKey: ["command-center-master-atlas"],
    queryFn: async (): Promise<MasterAtlasRelationshipMap> => {
      const data = await requestJson("/api/master-atlas");
      return (data ?? {}) as MasterAtlasRelationshipMap;
    },
    refetchInterval: LIVE_REFRESH_INTERVALS.overview,
    refetchIntervalInBackground: false,
  });

  if (overviewQuery.isError) {
    return (
      <div className="space-y-6">
        <ErrorPanel
          title="Command Center"
          description={
            overviewQuery.error instanceof Error
              ? overviewQuery.error.message
              : "Failed to load overview data."
          }
        />
      </div>
    );
  }

  const snapshot = overviewQuery.data ?? initialSnapshot;
  const masterAtlas =
    masterAtlasQuery.data && typeof masterAtlasQuery.data.generated_at === "string"
      ? masterAtlasQuery.data
      : null;
  const governedDispatch = masterAtlas?.governed_dispatch_execution ?? null;
  const governedDispatchStatusTone = handoffTone(governedDispatch);
  const governedDispatchRestartInterfering =
    governedDispatch?.resilience_state === "restart_interfering" ||
    governedDispatch?.advisory_blockers?.includes("agent_runtime_restart_interfering") ||
    false;
  const governedDispatchRecoveredFromRestart = governedDispatch?.recovery_reason === "server_restart";
  const workEconomyStatus =
    masterAtlas?.turnover_readiness?.work_economy_status ??
    masterAtlas?.summary?.self_acceleration_status ??
    null;
  const dispatchableQueueCount =
    masterAtlas?.turnover_readiness?.dispatchable_autonomous_queue_count ??
    masterAtlas?.summary?.autonomous_dispatchable_queue_count ??
    null;
  const topDispatchTitle =
    masterAtlas?.turnover_readiness?.top_dispatchable_autonomous_task_title ??
    masterAtlas?.summary?.autonomous_top_task_title ??
    governedDispatch?.current_task_title ??
    null;
  const degradedServices = snapshot.summary.degradedServices;
  const warningServices = snapshot.summary.warningServices;
  const pendingApprovals = snapshot.workforce.summary.pendingApprovals;
  const pendingTasks = snapshot.workforce.summary.pendingTasks;
  const runningTasks = snapshot.workforce.summary.runningTasks;
  const activeGoals = snapshot.workforce.summary.activeGoals;
  const activeProjects = snapshot.summary.activeProjects;
  const currentWorkplan = snapshot.workforce.workplan.current;
  const currentWorkplanApprovalCount = currentWorkplan?.tasks.filter((task) => task.requiresApproval).length ?? 0;
  const currentWorkplanTasks = currentWorkplan?.tasks.slice(0, 3) ?? [];
  const steadyState = snapshot.steadyState;
  const liveWorkCount = pendingTasks + runningTasks;
  const liveTone: SignalTone =
    governedDispatchRestartInterfering || degradedServices > 0
      ? "danger"
      : warningServices > 0 || pendingApprovals > 0 || pendingTasks > 0
        ? "warning"
        : "healthy";
  const proofDrilldowns: ProofDrilldownItem[] = [
    {
      href: "/operator",
      label: "Operator",
      description: "Approvals, overrides, and the live governance queue.",
    },
    {
      href: "/topology",
      label: "Topology",
      description: "Nodes, GPUs, services, and relationship proof.",
    },
    {
      href: "/routing",
      label: "Routing",
      description: "Lane policy, provider elasticity, and weak-lane truth.",
    },
    {
      href: "/subscriptions",
      label: "Subscriptions",
      description: "Burn economy, leases, and execution history.",
    },
    {
      href: "/more",
      label: "Route index",
      description: "The full launch map when you need breadth instead of triage.",
    },
  ];
  const routeOwnershipItems: RouteOwnershipItem[] = [
    {
      href: "/operator",
      label: "Operator",
      description: "Approvals, overrides, and governance controls.",
      metric: `${pendingApprovals} approvals`,
    },
    {
      href: "/backlog",
      label: "Backlog",
      description: "Dispatchable work and blocked queue items.",
      metric: `${pendingTasks} queued`,
    },
    {
      href: "/routing",
      label: "Routing",
      description: "Lane policy, provider elasticity, and execution selection.",
      metric: `${snapshot.summary.warningServices} warnings`,
    },
    {
      href: "/subscriptions",
      label: "Subscriptions",
      description: "Burn, leases, and execution history.",
      metric: "burn economy",
    },
  ];

  const triageItems: TriageItem[] = [
    ...(governedDispatchRestartInterfering
      ? [
          {
            href: "/routing",
            kicker: "Dispatch resilience",
            title: "Recent agent-runtime restarts are interrupting governed execution.",
            detail:
              "The current handoff is running on recovered auto-retry lineage. Fix the restart interference before trusting autonomous throughput.",
            metric: "restart interfering",
            tone: "danger" as const,
          },
        ]
      : []),
    {
      href: degradedServices > 0 ? "/services?status=degraded" : "/services?status=warning",
      kicker: "Service pressure",
      title:
        degradedServices > 0
          ? "Start with degraded services and active incidents."
          : "Warnings are clear enough to operate, but still worth checking.",
      detail:
        degradedServices > 0
          ? "Open the services surface first, then move into approval-held work."
          : "The services surface is stable enough for normal operation, with warnings under watch.",
      metric: `${degradedServices} degraded / ${warningServices} warning`,
      tone: degradedServices > 0 ? "danger" : warningServices > 0 ? "warning" : "healthy",
    },
    {
      href: "/operator",
      kicker: "Operator queue",
      title:
        pendingApprovals > 0
          ? "Manual decisions are waiting in the approval lane."
          : "No approval-held tasks are waiting on the operator.",
      detail: "Use the operator surface for approvals, overrides, and governance controls.",
      metric: `${pendingApprovals} approvals`,
      tone: pendingApprovals > 0 ? "warning" : "healthy",
    },
    {
      href: "/backlog",
      kicker: "Backlog pressure",
      title:
        pendingTasks > 0
          ? "Dispatchable work is stacking in the backlog."
          : "No queued local-safe work is waiting to be dispatched.",
      detail: "Keep self-improving work moving before browsing lower-frequency surfaces.",
      metric: `${pendingTasks} pending`,
      tone: pendingTasks > 0 ? "warning" : "healthy",
    },
    {
      href: "/projects",
      kicker: "Project load",
      title:
        activeProjects > 0
          ? "Promotion waves and tracked initiatives still need follow-through."
          : "No active project pressure is showing on the summary surface.",
      detail: "Projects owns milestones, promotion waves, and strategic execution detail.",
      metric: `${activeProjects} active`,
      tone: activeProjects > 0 ? "warning" : "healthy",
    },
  ];

  const operatorAttentionTone: SignalTone = steadyState?.needsYou
    ? 'danger'
    : steadyState && (steadyState.runtimePacketCount > 0 || steadyState.queueDispatchable > 0)
      ? 'warning'
      : 'healthy';
  const topAction =
    triageItems.find((item) => item.tone === "danger") ??
    triageItems.find((item) => item.tone === "warning") ??
    triageItems[0];
  const governedDispatchDetail = governedDispatchRestartInterfering
    ? `${topDispatchTitle ?? "The current governed handoff"} is on recovered auto-retry lineage after a server restart, and restart interference is still degrading execution confidence.`
    : governedDispatchRecoveredFromRestart
      ? `${topDispatchTitle ?? "The current governed handoff"} recovered from a recent server restart and is back in flight through the canonical backlog lane.`
      : topDispatchTitle
        ? `${topDispatchTitle} is the current governed handoff, with execution already flowing through the canonical backlog lane.`
        : "The master atlas publishes governed dispatch posture here when the handoff feed is available.";

  const signalRows =
    snapshot.alerts.length > 0
      ? snapshot.alerts.slice(0, 4).map((alert) => ({
          href: alert.href,
          kicker: "Alert",
          title: alert.title,
          detail: alert.description,
          tone:
            alert.tone === "degraded"
              ? ("danger" as const)
              : alert.tone === "warning"
                ? ("warning" as const)
                : ("healthy" as const),
        }))
      : snapshot.services
          .filter((service) => service.state !== "healthy")
          .slice(0, 4)
          .map((service) => ({
            href: "/services",
            kicker: service.node,
            title: service.name,
            detail:
              service.state === "degraded"
                ? service.lastError ?? "Service is degraded and needs intervention."
                : service.lastError ?? "Service is warning and worth watching.",
            tone: service.state === "degraded" ? ("danger" as const) : ("warning" as const),
          }));

  return (
    <div className="space-y-6 lg:space-y-7">
      <section className="surface-hero mission-divider relative overflow-hidden rounded-[1.2rem] border px-5 py-5 sm:px-6 sm:py-6">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.08),transparent_36%)]"
        />
        <div className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr] xl:gap-8">
          <div className="space-y-6">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">Mission Control</Badge>
                <Badge variant={topAction.tone === "danger" ? "destructive" : "outline"}>
                  {topAction.tone === "danger" ? "operator attention required" : "governed posture"}
                </Badge>
              </div>
              <div className="space-y-2">
                <p className="page-eyebrow">Command Center</p>
                <h1 className="display-sheen max-w-3xl font-sans text-3xl font-semibold tracking-[-0.05em] sm:text-4xl">
                  Current work, next move, and live pressure.
                </h1>
                <p className="max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)] sm:text-[15px]">
                  The front door should answer what is already in flight, what needs attention next, and where
                  the live pressure is coming from. Atlas depth, long histories, and specialist workflows belong
                  on the routes built for them.
                </p>
              </div>
            </div>

            <div className="surface-panel border border-primary/20 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">Current plan</Badge>
                {currentWorkplan ? (
                  <Badge>{currentWorkplan.planId}</Badge>
                ) : (
                  <Badge variant="destructive">No plan loaded</Badge>
                )}
                {currentWorkplan ? <Badge variant="outline">{currentWorkplan.taskCount} tasks</Badge> : null}
                {snapshot.workforce.workplan.needsRefill ? (
                  <Badge variant="destructive">Needs refill</Badge>
                ) : (
                  <Badge variant="secondary">Ready</Badge>
                )}
              </div>
              <h2 className="mt-3 font-sans text-2xl font-semibold tracking-[-0.04em] text-foreground">
                {currentWorkplan?.focus ?? "No current plan is loaded yet."}
              </h2>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">
                {currentWorkplan?.timeContext
                  ? `${currentWorkplan.timeContext} · refreshed ${formatRelativeTime(currentWorkplan.generatedAt)}.`
                  : "Use the workforce planner to generate the next plan."}
              </p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
                <span className="rounded-full border border-border/70 px-2.5 py-1">{liveWorkCount} live items</span>
                <span className="rounded-full border border-border/70 px-2.5 py-1">{pendingApprovals} approvals</span>
                <span className="rounded-full border border-border/70 px-2.5 py-1">{activeGoals} active goals</span>
                <span className="rounded-full border border-border/70 px-2.5 py-1">
                  {currentWorkplanApprovalCount} plan approvals
                </span>
              </div>
              <div className="mt-4 space-y-2">
                {currentWorkplan ? (
                  currentWorkplanTasks.map((task) => <WorkplanTaskRow key={task.taskId} task={task} />)
                ) : (
                  <p className="rounded-2xl border border-dashed border-border/70 px-4 py-4 text-sm text-muted-foreground">
                    No workplan is loaded yet. Open the workforce planner to generate the next pass.
                  </p>
                )}
              </div>
              <Button asChild variant="outline" size="sm" className="mt-4">
                <Link href="/workforce">Open workforce planner</Link>
              </Button>
            </div>

            <div className="overflow-hidden border-y border-border/70 bg-border/20 sm:grid sm:grid-cols-4">
              <MetricCell
                label="Services"
                value={`${snapshot.summary.healthyServices}/${snapshot.summary.totalServices}`}
                detail={degradedServices > 0 ? `${degradedServices} degraded` : `${warningServices} warnings under watch`}
                tone={degradedServices > 0 ? "danger" : warningServices > 0 ? "warning" : "healthy"}
              />
              <MetricCell
                label="Approvals"
                value={`${pendingApprovals}`}
                detail="Approval-held tasks"
                tone={pendingApprovals > 0 ? "warning" : "healthy"}
              />
              <MetricCell
                label="Live work"
                value={`${liveWorkCount}`}
                detail={`${pendingTasks} queued, ${runningTasks} running`}
                tone={pendingTasks > 0 ? "warning" : "healthy"}
              />
              <MetricCell
                label="GPU Avg"
                value={formatPercent(snapshot.summary.averageGpuUtilization, 0)}
                detail={`${snapshot.nodes.length} nodes reporting`}
                tone={
                  snapshot.summary.averageGpuUtilization !== null &&
                  snapshot.summary.averageGpuUtilization >= 80
                    ? "warning"
                    : "healthy"
                }
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="page-eyebrow">Priority Queue</p>
                  <p className="text-sm text-muted-foreground">
                    These are the first places to spend attention on this pass.
                  </p>
                </div>
                <Button asChild variant="outline" size="sm">
                  <Link href="/backlog">Open backlog</Link>
                </Button>
              </div>
              <div className="overflow-hidden border-y border-border/70 bg-[color:var(--surface-panel)]">
                {triageItems.map((item) => (
                  <TriageRow key={item.kicker} item={item} />
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="surface-panel border border-primary/20 p-4">
              <p className="page-eyebrow">Next Move</p>
              <h2 className="mt-2 font-sans text-2xl font-semibold tracking-[-0.04em] text-foreground">
                {topAction.title}
              </h2>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{topAction.detail}</p>
              <div className="mt-4 flex items-center gap-2">
                <StatusDot tone={topAction.tone} pulse={topAction.tone !== "healthy"} />
                <p className={cn("text-sm font-semibold", toneText(topAction.tone))}>{topAction.metric}</p>
              </div>
              <Button asChild className="mt-5 w-full justify-between">
                <Link href={topAction.href}>
                  Open this surface
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>

            <div className="surface-panel border border-border/70 p-4">
              <p className="page-eyebrow">Operator attention</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Badge variant={operatorAttentionTone === 'danger' ? 'destructive' : operatorAttentionTone === 'warning' ? 'outline' : 'secondary'}>
                  {steadyState?.interventionLabel ?? 'Review recommended'}
                </Badge>
                {steadyState?.currentWork?.providerLabel ? <Badge variant="outline">{steadyState.currentWork.providerLabel}</Badge> : null}
                {steadyState?.nextUp?.laneFamily ? <Badge variant="outline">{steadyState.nextUp.laneFamily}</Badge> : null}
              </div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">
                {steadyState?.interventionSummary ?? 'Use the operator desk for approvals, overrides, and governed blockers.'}
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <LiveReadoutRow
                  label="Needs you"
                  value={steadyState?.needsYou ? 'Yes' : 'No'}
                  tone={steadyState?.needsYou ? 'danger' : 'healthy'}
                />
                <LiveReadoutRow
                  label="Decision queue"
                  value={`${pendingApprovals} approvals / ${steadyState?.runtimePacketCount ?? 0} runtime packets`}
                  tone={pendingApprovals > 0 || (steadyState?.runtimePacketCount ?? 0) > 0 ? 'warning' : 'healthy'}
                />
              </div>
              <p className="mt-4 text-xs leading-5 text-muted-foreground">
                {steadyState?.nextOperatorAction ?? 'Open the operator desk when approvals or runtime packets appear.'}
              </p>
              <Button asChild variant="outline" size="sm" className="mt-4 w-full justify-between">
                <Link href="/operator">
                  Open operator desk
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>

            <div className="surface-panel border border-border/70 p-4">
              <p className="page-eyebrow">Specialist routes</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Depth lives on the specialist routes. Keep the front door focused on the current plan, next move,
                and live pressure.
              </p>
              <div className="mt-4 space-y-4">
                <div className="surface-instrument rounded-2xl border border-border/70 px-4 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="page-eyebrow text-[10px]">First Read</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Live posture first, then proof surfaces for deeper drilling.
                      </p>
                    </div>
                    <Badge variant="outline">{formatRelativeTime(snapshot.generatedAt)}</Badge>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div className="space-y-3">
                      <LiveReadoutRow
                        label="System state"
                        value={steadyState?.closureState ?? governedDispatch?.status ?? "steady-state monitoring"}
                        tone={liveTone}
                      />
                      <LiveReadoutRow
                        label="Attention"
                        value={steadyState?.interventionLabel ?? (
                          topAction.tone === "danger"
                            ? "operator attention required"
                            : pendingApprovals > 0 || pendingTasks > 0
                              ? "review recommended"
                              : "no action needed"
                        )}
                        tone={
                          topAction.tone === "danger"
                            ? "danger"
                            : pendingApprovals > 0 || pendingTasks > 0
                              ? "warning"
                              : "healthy"
                        }
                      />
                      <LiveReadoutRow
                        label="Current work"
                        value={steadyState?.currentWork?.taskTitle ?? currentWorkplan?.focus ?? "No current plan loaded"}
                        tone={steadyState?.currentWork?.taskTitle || currentWorkplan ? "healthy" : "warning"}
                      />
                    </div>
                    <div className="space-y-3">
                      <LiveReadoutRow label="Next up" value={steadyState?.nextUp?.taskTitle ?? topAction.title} tone="warning" />
                      <LiveReadoutRow
                        label="Queue posture"
                        value={steadyState ? `${steadyState.queueDispatchable} dispatchable / ${steadyState.suppressedTaskCount} suppressed / ${steadyState.runtimePacketCount} runtime packets` : `${pendingTasks} queued / ${runningTasks} running / ${pendingApprovals} approvals`}
                        tone={steadyState ? (steadyState.needsYou || steadyState.runtimePacketCount > 0 ? "warning" : "healthy") : (pendingTasks > 0 || pendingApprovals > 0 ? "warning" : "healthy")}
                      />
                      <LiveReadoutRow
                        label="Updated"
                        value={formatRelativeTime(snapshot.generatedAt)}
                        tone="healthy"
                      />
                    </div>
                  </div>
                  <div className="mt-4 border-t border-border/70 pt-4">
                    <p className="page-eyebrow text-[10px]">Proof drill-down</p>
                    <div className="mt-3 grid gap-2">
                      {proofDrilldowns.map((item) => (
                        <ProofDrilldownRow key={item.href} item={item} />
                      ))}
                    </div>
                  </div>
                </div>
                <div className="surface-instrument rounded-2xl border px-4 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="page-eyebrow text-[10px]">Autonomous handoff</p>
                    <Badge
                      variant={
                        governedDispatchStatusTone === "danger"
                          ? "destructive"
                          : governedDispatchStatusTone === "healthy"
                            ? "secondary"
                            : "outline"
                      }
                    >
                      {governedDispatch?.task_status ?? governedDispatch?.status ?? "handoff pending"}
                    </Badge>
                    {governedDispatch?.governor_level ? (
                      <Badge variant="outline">Level {governedDispatch.governor_level}</Badge>
                    ) : null}
                    {workEconomyStatus ? <Badge variant="outline">{workEconomyStatus}</Badge> : null}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {governedDispatchDetail}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    {governedDispatch?.backlog_status ? (
                      <span className="rounded-full border border-border/70 px-2.5 py-1">
                        backlog {governedDispatch.backlog_status}
                      </span>
                    ) : null}
                    {dispatchableQueueCount != null ? (
                      <span className="rounded-full border border-border/70 px-2.5 py-1">
                        {dispatchableQueueCount} dispatchable
                      </span>
                    ) : null}
                    {governedDispatch?.dispatch_outcome ? (
                      <span className="rounded-full border border-border/70 px-2.5 py-1">
                        {governedDispatch.dispatch_outcome}
                      </span>
                    ) : null}
                    {governedDispatch?.task_source ? (
                      <span className="rounded-full border border-border/70 px-2.5 py-1">
                        {governedDispatch.task_source}
                      </span>
                    ) : null}
                    {governedDispatch?.recovery_reason ? (
                      <span className="rounded-full border border-border/70 px-2.5 py-1">
                        recovered from {governedDispatch.recovery_reason.replaceAll("_", " ")}
                      </span>
                    ) : null}
                    {governedDispatch?.resilience_state ? (
                      <span className="rounded-full border border-border/70 px-2.5 py-1">
                        {governedDispatch.resilience_state.replaceAll("_", " ")}
                      </span>
                    ) : null}
                  </div>
                </div>
                {routeOwnershipItems.map((route) => (
                  <RouteOwnershipRow key={route.href} route={route} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <section className="surface-panel overflow-hidden rounded-[1.25rem] border">
          <div className="border-b border-border/70 px-4 py-4 sm:px-5">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-primary" />
              <div>
                <p className="text-sm font-medium text-foreground">Critical Signals</p>
                <p className="text-xs text-muted-foreground">
                  The clearest operator-facing pressure surfaced from alerts and current service posture.
                </p>
              </div>
            </div>
          </div>
          {signalRows.length > 0 ? (
            signalRows.map((signal) => (
              <SignalRow
                key={`${signal.kicker}-${signal.title}`}
                href={signal.href}
                kicker={signal.kicker}
                title={signal.title}
                detail={signal.detail}
                tone={signal.tone}
              />
            ))
          ) : (
            <div className="px-4 py-5 sm:px-5">
              <p className="text-sm font-medium text-foreground">No active alerts are breaking through right now.</p>
              <p className="mt-1 text-xs text-muted-foreground">
                The services surface is still the right place for deeper drill-down and warning history.
              </p>
            </div>
          )}
        </section>

        <section className="surface-panel overflow-hidden rounded-[1.25rem] border">
          <div className="border-b border-border/70 px-4 py-4 sm:px-5">
            <div className="flex items-center gap-2">
              <Workflow className="h-4 w-4 text-primary" />
              <div>
                <p className="text-sm font-medium text-foreground">Cluster Posture</p>
                <p className="text-xs text-muted-foreground">
                  Node-level service posture and GPU load without making the home page a topology screen.
                </p>
              </div>
            </div>
          </div>
          {snapshot.nodes.map((node) => (
            <NodeRow key={node.id} node={node} />
          ))}
        </section>
      </div>

    </div>
  );
}
