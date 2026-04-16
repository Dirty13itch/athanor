"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Activity, BarChart3, DollarSign, Network, RefreshCcw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import type { MasterAtlasRelationshipMap } from "@/lib/master-atlas";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";
import { requestJson } from "@/features/workforce/helpers";

interface RoutingLogEntry {
  task_id?: string;
  policy_class?: string;
  execution_lane?: string;
  provider?: string;
  outcome?: string;
  timestamp?: string;
}

interface ProviderStatus {
  id?: string;
  name: string;
  subscription?: string;
  monthly_cost?: number | null;
  pricing_status?: string;
  category?: string;
  status?: string;
  provider_state?: string;
  execution_mode?: string;
  tasks_today?: number;
  avg_latency_ms?: number;
}

interface MaterializedBacklogPayload {
  backlog_id?: string | null;
  title?: string | null;
  already_materialized?: boolean;
  backlog?: {
    id?: string;
    title?: string;
    status?: string;
  } | null;
}

interface BacklogDispatchPayload {
  backlog?: {
    id?: string;
    status?: string;
  } | null;
  task?: {
    id?: string;
    status?: string;
  } | null;
}

function sentenceCase(value: string | null | undefined) {
  if (!value) return "unknown";
  return value.replaceAll("_", " ");
}

function compactTaskLabel(taskId: string | null | undefined) {
  if (!taskId) return "No dispatchable task";
  const normalized = taskId.startsWith("workstream:") ? taskId.replace("workstream:", "") : taskId;
  return normalized.replaceAll("-", " ");
}

function policyBadgeVariant(policyClass: string | undefined) {
  switch (policyClass) {
    case "local_only":
      return "outline" as const;
    case "cli_review":
      return "secondary" as const;
    case "cloud_escalation":
      return "destructive" as const;
    default:
      return "default" as const;
  }
}

function outcomeBadgeVariant(outcome: string | undefined) {
  if (outcome === "success") return "outline" as const;
  if (outcome === "fail" || outcome === "failed") return "destructive" as const;
  return "default" as const;
}

function statusDot(status: string | undefined) {
  if (status === "healthy" || status === "active" || status === "online") {
    return "bg-[color:var(--signal-success)]";
  }
  if (status === "degraded" || status === "warning") {
    return "bg-[color:var(--signal-warning)]";
  }
  if (status === "down" || status === "offline" || status === "error") {
    return "bg-[color:var(--signal-danger)]";
  }
  return "bg-muted-foreground";
}

function formatPolicyLabel(policyClass: string | undefined) {
  if (!policyClass) return "unclassified";
  return policyClass.replaceAll("_", " ");
}

export function RoutingConsole() {
  const [materializeBusy, setMaterializeBusy] = useState(false);
  const [materializeFeedback, setMaterializeFeedback] = useState<string | null>(null);
  const [materializedBacklogId, setMaterializedBacklogId] = useState<string | null>(null);
  const [dispatchBusy, setDispatchBusy] = useState(false);
  const [dispatchFeedback, setDispatchFeedback] = useState<string | null>(null);
  const operatorSession = useOperatorSessionStatus();
  const sessionLocked = isOperatorSessionLocked(operatorSession);
  const routingReadEnabled = !operatorSession.isPending && !sessionLocked;

  const logQuery = useQuery({
    queryKey: ["routing-log"],
    queryFn: async (): Promise<RoutingLogEntry[]> => {
      const data = await requestJson("/api/routing/log?limit=30");
      return (data?.entries ?? data ?? []) as RoutingLogEntry[];
    },
    enabled: routingReadEnabled,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const providersQuery = useQuery({
    queryKey: ["routing-providers"],
    queryFn: async (): Promise<ProviderStatus[]> => {
      const data = await requestJson("/api/routing/providers");
      return (data?.providers ?? data ?? []) as ProviderStatus[];
    },
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const masterAtlasQuery = useQuery({
    queryKey: ["routing-master-atlas"],
    queryFn: async (): Promise<MasterAtlasRelationshipMap> => {
      const data = await requestJson("/api/master-atlas");
      return (data ?? {}) as MasterAtlasRelationshipMap;
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const logEntries = logQuery.data ?? [];
  const providers = providersQuery.data ?? [];
  const masterAtlas =
    masterAtlasQuery.data && typeof masterAtlasQuery.data.generated_at === "string"
      ? masterAtlasQuery.data
      : null;
  const turnoverReadiness = masterAtlas?.turnover_readiness ?? null;
  const autonomousQueue = masterAtlas?.autonomous_queue_summary ?? null;
  const governedDispatchState = masterAtlas?.governed_dispatch_state ?? null;
  const governedDispatchExecution = masterAtlas?.governed_dispatch_execution ?? null;
  const safeSurfaceSummary = masterAtlas?.safe_surface_summary ?? null;
  const laneRecommendations = masterAtlas?.lane_recommendations ?? [];
  const quotaPosture = masterAtlas?.quota_posture ?? null;
  const nextRequiredApproval = masterAtlas?.next_required_approval ?? null;
  const governedDispatchClaim = autonomousQueue?.governed_dispatch_claim ?? null;
  const capacityHarvest = turnoverReadiness?.capacity_harvest_summary ?? null;
  const governedDispatchMaterialization = governedDispatchState?.materialization ?? null;
  const governedDispatchExecutionReportPath =
    masterAtlas?.governed_dispatch_execution_report_path ?? governedDispatchExecution?.report_path ?? null;

  const totalRouted = logEntries.length;
  const localOnly = logEntries.filter((entry) => entry.policy_class === "local_only").length;
  const cliReviewed = logEntries.filter((entry) => entry.policy_class === "cli_review").length;
  const cloudEscalation = logEntries.filter((entry) => entry.policy_class === "cloud_escalation").length;
  const healthyProviders = providers.filter((provider) =>
    ["healthy", "active", "online"].includes(provider.status ?? "")
  ).length;
  const degradedProviders = providers.filter((provider) =>
    ["degraded", "warning", "down", "offline", "error"].includes(provider.status ?? "")
  ).length;
  const routeNextAction =
    governedDispatchState?.current_task_title ??
    governedDispatchClaim?.current_task_title ??
    autonomousQueue?.top_dispatchable_title ??
    turnoverReadiness?.top_dispatchable_autonomous_task_title ??
    (cloudEscalation > 0
      ? "Review escalation lanes before widening cloud burn."
      : "Routing is staying local-first; keep provider lanes warm.");
  const localPct = totalRouted > 0 ? `${((localOnly / totalRouted) * 100).toFixed(0)}%` : "--";
  const cliPct = totalRouted > 0 ? `${((cliReviewed / totalRouted) * 100).toFixed(0)}%` : "--";
  const dispatchPhase = sentenceCase(turnoverReadiness?.burn_dispatch_phase_label ?? "unknown");
  const providerGateState = sentenceCase(turnoverReadiness?.provider_gate_state ?? "unknown");
  const workEconomyStatus = sentenceCase(turnoverReadiness?.work_economy_status ?? "unknown");
  const queueTotalCount = autonomousQueue?.queue_count ?? turnoverReadiness?.autonomous_queue_count ?? 0;
  const dispatchQueueCount =
    autonomousQueue?.dispatchable_queue_count ?? turnoverReadiness?.dispatchable_autonomous_queue_count ?? 0;
  const approvalHeldCount = autonomousQueue?.blocked_queue_count ?? 0;
  const topDispatchTask =
    governedDispatchState?.current_task_title ??
    governedDispatchClaim?.current_task_title ??
    autonomousQueue?.top_dispatchable_title ??
    turnoverReadiness?.top_dispatchable_autonomous_task_title ??
    compactTaskLabel(
      autonomousQueue?.top_dispatchable_task_id ?? turnoverReadiness?.top_dispatchable_autonomous_task_id ?? null
    );
  const topDispatchLane =
    governedDispatchState?.preferred_lane_family != null
      ? sentenceCase(governedDispatchState.preferred_lane_family)
      : governedDispatchClaim?.preferred_lane_family != null
      ? sentenceCase(governedDispatchClaim.preferred_lane_family)
      : autonomousQueue?.top_dispatchable_lane_family != null
      ? sentenceCase(autonomousQueue.top_dispatchable_lane_family)
      : null;
  const claimedDispatchTask =
    governedDispatchState?.current_task_title ??
    governedDispatchClaim?.current_task_title ??
    compactTaskLabel(governedDispatchClaim?.current_task_id ?? safeSurfaceSummary?.governed_current_task_id ?? null);
  const claimedDispatchOnDeck =
    governedDispatchState?.on_deck_task_title ??
    governedDispatchClaim?.on_deck_task_title ??
    compactTaskLabel(governedDispatchClaim?.on_deck_task_id ?? safeSurfaceSummary?.governed_on_deck_task_id ?? null);
  const claimedDispatchMutation =
    governedDispatchState?.approved_mutation_label ??
    governedDispatchClaim?.approved_mutation_label ??
    sentenceCase(governedDispatchClaim?.approved_mutation_class ?? undefined);
  const dispatchProofSurface =
    governedDispatchState?.proof_command_or_eval_surface ?? governedDispatchClaim?.proof_command_or_eval_surface ?? null;
  const dispatchRuntimeStatus = sentenceCase(
    governedDispatchExecution?.status ??
      governedDispatchState?.status ??
      governedDispatchClaim?.status ??
      safeSurfaceSummary?.governed_dispatch_status
  );
  const dispatchRuntimeOutcome = sentenceCase(
    governedDispatchExecution?.dispatch_outcome ??
      governedDispatchExecution?.status ??
      governedDispatchState?.dispatch_outcome ??
      governedDispatchClaim?.status ??
      "unknown"
  );
  const governedExecutionStatus = sentenceCase(governedDispatchExecution?.status ?? "not recorded");
  const governedExecutionOutcome = sentenceCase(governedDispatchExecution?.dispatch_outcome ?? "unknown");
  const governedExecutionBacklogId = governedDispatchExecution?.backlog_id ?? null;
  const governedExecutionTaskStatus = sentenceCase(governedDispatchExecution?.task_status ?? "unknown");
  const governedExecutionTaskId = governedDispatchExecution?.task_id ?? null;
  const governedExecutionTaskSource = governedDispatchExecution?.task_source ?? null;
  const governedExecutionGovernorLevel = governedDispatchExecution?.governor_level ?? null;
  const governedExecutionGovernorReason = governedDispatchExecution?.governor_reason ?? null;
  const governedExecutionRecoveryReason = sentenceCase(governedDispatchExecution?.recovery_reason ?? "unknown");
  const governedExecutionRetryDepth = governedDispatchExecution?.retry_lineage_depth ?? 0;
  const governedExecutionRetryOfTaskId = governedDispatchExecution?.retry_of_task_id ?? null;
  const governedExecutionResilienceState = governedDispatchExecution?.resilience_state ?? null;
  const governedExecutionAlreadyRecorded =
    governedDispatchExecution?.status === "dispatched" || Boolean(governedExecutionTaskId);
  const governedDispatchArtifactPath = governedDispatchState?.report_path ?? null;
  const governedMaterializationStatus = sentenceCase(governedDispatchMaterialization?.status ?? "not_materialized");
  const governedMaterializationBacklogId = governedDispatchMaterialization?.backlog_id ?? null;
  const governedMaterializationReportPath = governedDispatchMaterialization?.report_path ?? null;
  const governedMaterializationError = governedDispatchMaterialization?.error ?? null;
  const effectiveMaterializedBacklogId = materializedBacklogId ?? governedMaterializationBacklogId;
  const dispatchMaterializedButtonLabel = governedExecutionAlreadyRecorded
    ? "Execution Recorded"
    : dispatchBusy
      ? "Dispatching..."
      : "Dispatch Materialized Item";
  const canDispatchMaterializedBacklog =
    Boolean(effectiveMaterializedBacklogId) && !dispatchBusy && !governedExecutionAlreadyRecorded;
  const safeSurfaceQueueLine =
    governedDispatchState != null
      ? `${governedDispatchState.dispatchable_queue_count ?? 0} governed dispatchable of ${
          governedDispatchState.queue_count ?? 0
        } total | ${governedDispatchState.safe_surface_dispatchable_queue_count ?? 0} safe-surface dispatchable of ${
          governedDispatchState.safe_surface_queue_count ?? 0
        } total`
      : `${dispatchQueueCount} governed dispatchable of ${queueTotalCount} total`;
  const nextApprovalActions =
    nextRequiredApproval?.allowed_actions?.length
      ? nextRequiredApproval.allowed_actions.slice(0, 3).map((action) => sentenceCase(action)).join(" | ")
      : null;
  const harvestAdmissionState = sentenceCase(capacityHarvest?.admission_state ?? "unknown");
  const harvestableSlotCount =
    capacityHarvest?.harvestable_scheduler_slot_count ??
    quotaPosture?.local_compute_capacity?.harvestable_scheduler_slot_count ??
    0;
  const reserveHeldSlotCount = capacityHarvest?.protected_reserve_slot_count ?? 0;
  const schedulerQueueDepth =
    capacityHarvest?.scheduler_queue_depth ?? quotaPosture?.local_compute_capacity?.scheduler_queue_depth ?? 0;
  const routingPairs = laneRecommendations.slice(0, 3);

  async function handleMaterializeGovernedDispatch() {
    setMaterializeBusy(true);
    setMaterializeFeedback(null);
    setDispatchFeedback(null);
    try {
      const payload = (await requestJson("/api/operator/backlog/materialize-governed-dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      })) as MaterializedBacklogPayload | null;
      const backlogId = payload?.backlog_id ?? payload?.backlog?.id ?? null;
      const backlogTitle =
        payload?.title ??
        payload?.backlog?.title ??
        governedDispatchState?.current_task_title ??
        "Governed dispatch claim";
      const backlogStatus = payload?.backlog?.status ?? null;
      setMaterializedBacklogId(backlogId);
      await masterAtlasQuery.refetch();
      if (payload?.already_materialized) {
        setMaterializeFeedback(
          `${backlogTitle} already exists in operator backlog${backlogId ? ` as ${backlogId}` : ""}.`
        );
      } else {
        setMaterializeFeedback(
          `${backlogTitle} is now materialized in operator backlog${backlogId ? ` as ${backlogId}` : ""}${
            backlogStatus ? ` (${backlogStatus})` : ""
          }.`
        );
      }
    } catch (error) {
      setMaterializeFeedback(error instanceof Error ? error.message : "Failed to materialize governed dispatch.");
    } finally {
      setMaterializeBusy(false);
    }
  }

  async function handleDispatchMaterializedBacklog() {
    if (!effectiveMaterializedBacklogId) {
      return;
    }

    setDispatchBusy(true);
    setDispatchFeedback(null);
    try {
      const payload = (await requestJson(
        `/api/operator/backlog/${encodeURIComponent(effectiveMaterializedBacklogId)}/dispatch`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        }
      )) as BacklogDispatchPayload | null;
      const taskId = payload?.task?.id ?? null;
      const backlogStatus = payload?.backlog?.status ?? null;
      await masterAtlasQuery.refetch();
      setDispatchFeedback(
        `Dispatched ${effectiveMaterializedBacklogId}${taskId ? ` to task ${taskId}` : ""}${
          backlogStatus ? ` (${backlogStatus})` : ""
        }.`
      );
    } catch (error) {
      setDispatchFeedback(error instanceof Error ? error.message : "Failed to dispatch materialized backlog item.");
    } finally {
      setDispatchBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Intelligence"
        title="Routing & Cost"
        description="Execution-lane visibility and provider health. Burn posture now lives in Subscriptions, so this page stays focused on where work went and which lanes still need repair."
        attentionHref="/routing"
        actions={
          <>
            <Button asChild variant="outline">
              <Link href="/subscriptions">Open Subscriptions</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/operator">Open Operator</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/topology">Open Topology</Link>
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                void logQuery.refetch();
                void providersQuery.refetch();
                void masterAtlasQuery.refetch();
              }}
              disabled={sessionLocked || logQuery.isFetching || providersQuery.isFetching || masterAtlasQuery.isFetching}
            >
              <RefreshCcw
                className={`mr-2 h-4 w-4 ${logQuery.isFetching || providersQuery.isFetching || masterAtlasQuery.isFetching ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Tasks Routed"
            value={`${totalRouted}`}
            detail="Recent routing window"
            icon={<Network className="h-5 w-5" />}
          />
          <StatCard
            label="Local-only"
            value={localPct}
            detail={`${localOnly} of ${totalRouted} decisions`}
            icon={<Activity className="h-5 w-5" />}
            tone={localPct !== "--" && parseInt(localPct, 10) >= 80 ? "success" : "default"}
          />
          <StatCard
            label="CLI reviewed"
            value={cliPct}
            detail={`${cliReviewed} of ${totalRouted} decisions`}
            icon={<BarChart3 className="h-5 w-5" />}
          />
          <StatCard
            label="Burn posture"
            value="Subscriptions"
            detail="Spend, leases, and handoffs live there."
            icon={<DollarSign className="h-5 w-5" />}
          />
        </div>
      </PageHeader>

      <section className="surface-panel rounded-[30px] border px-5 py-5 sm:px-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="page-eyebrow">Routing spine</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">
              Execution lanes first, burn second
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              This route should read like a specialist control surface: where work went, which policy class governed it, and whether the providers still look healthy enough to keep routing open.
            </p>
          </div>
          <div className="surface-instrument rounded-2xl border px-4 py-3 lg:min-w-[20rem]">
            <p className="page-eyebrow text-[10px]">Next action</p>
            <p className="mt-1 text-sm font-medium text-foreground">{routeNextAction}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {dispatchQueueCount} dispatchable of {queueTotalCount} total
              {approvalHeldCount > 0 ? ` | ${approvalHeldCount} approval held` : " | no approval-held queue debt"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {nextRequiredApproval?.label
                ? `Next approval: ${nextRequiredApproval.label}`
                : "Open Subscriptions for burn and leases; open Operator for approvals and interventions."}
            </p>
          </div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Local-first</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">{localPct}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {localOnly} of {totalRouted} decisions
            </p>
          </div>
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">CLI reviewed</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">{cliPct}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {cliReviewed} of {totalRouted} decisions
            </p>
          </div>
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Providers healthy</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">{healthyProviders}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {providers.length > 0 ? `${degradedProviders} degraded` : "No provider sample"}
            </p>
          </div>
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Cloud escalation</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">{cloudEscalation}</p>
            <p className="mt-1 text-xs text-muted-foreground">Premium or fallback lane usage</p>
          </div>
        </div>
      </section>

      <section className="surface-panel rounded-[30px] border px-5 py-5 sm:px-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="page-eyebrow">Dispatch Economy</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">
              Live compounding posture
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              This is the control-plane read on what the system can safely dispatch right now, which gate still matters, and whether the burn economy is healthy enough to keep compounding.
            </p>
          </div>
          <div className="surface-instrument rounded-2xl border px-4 py-3 lg:min-w-[20rem]">
            <p className="page-eyebrow text-[10px]">Dispatch phase</p>
            <p className="mt-1 text-sm font-medium text-foreground">{dispatchPhase}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {dispatchQueueCount} dispatchable task{dispatchQueueCount === 1 ? "" : "s"} in the ranked autonomous queue
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {queueTotalCount} total
              {approvalHeldCount > 0 ? ` | ${approvalHeldCount} approval held` : " | no approval-held items"}
            </p>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Provider gate</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">{providerGateState}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {turnoverReadiness?.provider_elasticity_limited ? "Elasticity still limited" : "No turnover-critical provider blocker"}
            </p>
          </div>
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Work economy</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">{workEconomyStatus}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {turnoverReadiness?.self_acceleration_status
                ? sentenceCase(turnoverReadiness.self_acceleration_status)
                : "Self-acceleration posture unavailable"}
            </p>
          </div>
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Top dispatch</p>
            <p className="mt-1 text-lg font-semibold tracking-tight">{topDispatchTask}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {topDispatchLane ? `${topDispatchLane} lane family` : "Lane family unavailable"}
            </p>
          </div>
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Harvest admission</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">{harvestAdmissionState}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {capacityHarvest
                ? `${harvestableSlotCount} harvestable slot${harvestableSlotCount === 1 ? "" : "s"} | ${reserveHeldSlotCount} reserve-held | queue depth ${schedulerQueueDepth}`
                : "Capacity harvest summary unavailable"}
            </p>
          </div>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(19rem,0.85fr)]">
          <div className="surface-instrument rounded-2xl border px-4 py-4">
            <p className="page-eyebrow text-[10px]">Dispatch posture</p>
            <div className="mt-3 space-y-4">
              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">Dispatch runtime</p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    {dispatchRuntimeStatus}
                  </Badge>
                  <Badge variant="outline" className="text-[10px]">
                    Outcome: {dispatchRuntimeOutcome}
                  </Badge>
                  {governedDispatchState?.provider_gate_state ? (
                    <Badge variant="outline" className="text-[10px]">
                      Provider gate: {sentenceCase(governedDispatchState.provider_gate_state)}
                    </Badge>
                  ) : null}
                  {governedDispatchState?.work_economy_status ? (
                    <Badge variant="outline" className="text-[10px]">
                      Work economy: {sentenceCase(governedDispatchState.work_economy_status)}
                    </Badge>
                  ) : null}
                </div>
                <p className="text-xs text-muted-foreground">{safeSurfaceQueueLine}</p>
                {governedDispatchArtifactPath ? (
                  <p className="font-mono text-xs text-muted-foreground">{governedDispatchArtifactPath}</p>
                ) : null}
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">Current governed item</p>
                <p className="text-sm text-muted-foreground">{claimedDispatchTask}</p>
                <p className="text-xs text-muted-foreground">
                  {topDispatchLane ? `${topDispatchLane} | ` : ""}
                  {claimedDispatchMutation ?? "Mutation class unavailable"}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">On deck</p>
                <p className="text-sm text-muted-foreground">{claimedDispatchOnDeck}</p>
                <p className="text-xs text-muted-foreground">
                  {approvalHeldCount > 0
                    ? `${approvalHeldCount} approval-held item${approvalHeldCount === 1 ? "" : "s"} still behind the governed queue.`
                  : "No approval-held item is leading the queue."}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">Backlog materialization</p>
                <p className="text-sm text-muted-foreground">
                  {governedMaterializationBacklogId
                    ? `${governedMaterializationStatus} as ${governedMaterializationBacklogId}`
                    : governedMaterializationStatus}
                </p>
                {governedMaterializationError ? (
                  <p className="text-xs text-muted-foreground">{governedMaterializationError}</p>
                ) : governedMaterializationReportPath ? (
                  <p className="font-mono text-xs text-muted-foreground">{governedMaterializationReportPath}</p>
                ) : null}
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">Execution handoff</p>
                <p className="text-sm text-muted-foreground">
                  {governedDispatchExecution
                    ? `${governedExecutionStatus}${governedExecutionBacklogId ? ` for ${governedExecutionBacklogId}` : ""}`
                    : "No execution record yet."}
                </p>
                <p className="text-xs text-muted-foreground">
                  {governedDispatchExecution
                    ? `${governedExecutionOutcome}${governedExecutionTaskId ? ` | task ${governedExecutionTaskId}` : ""}${governedExecutionTaskStatus ? ` (${governedExecutionTaskStatus})` : ""}`
                    : "Dispatch the materialized backlog item to create an execution record."}
                </p>
                {governedExecutionResilienceState ? (
                  <p className="text-xs text-muted-foreground">
                    {governedExecutionResilienceState === "restart_interfering"
                      ? `Recent agent-runtime restarts are interrupting this handoff${governedExecutionTaskId ? ` at ${governedExecutionTaskId}` : ""}. The queue is preserving lineage and recovering through retry.`
                      : `Recovered through retry lineage${governedExecutionRetryDepth > 0 ? ` (${governedExecutionRetryDepth} hop${governedExecutionRetryDepth === 1 ? "" : "s"})` : ""}${governedExecutionRetryOfTaskId ? ` from ${governedExecutionRetryOfTaskId}` : ""}${governedExecutionRecoveryReason !== "Unknown" ? ` after ${governedExecutionRecoveryReason}` : ""}${governedExecutionTaskSource ? ` via ${governedExecutionTaskSource}` : ""}.`}
                  </p>
                ) : null}
                {governedExecutionGovernorLevel || governedExecutionGovernorReason ? (
                  <p className="text-xs text-muted-foreground">
                    Governor
                    {governedExecutionGovernorLevel ? ` ${governedExecutionGovernorLevel}` : ""}
                    {governedExecutionGovernorReason ? ` | ${governedExecutionGovernorReason}` : ""}
                  </p>
                ) : null}
                {governedDispatchExecutionReportPath ? (
                  <p className="font-mono text-xs text-muted-foreground">{governedDispatchExecutionReportPath}</p>
                ) : null}
              </div>
              {dispatchProofSurface ? (
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">Proof surface</p>
                  <p className="font-mono text-xs text-muted-foreground">{dispatchProofSurface}</p>
                </div>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onClick={() => void handleMaterializeGovernedDispatch()}
                  disabled={materializeBusy || !governedDispatchState?.current_task_id}
                >
                  {materializeBusy ? "Materializing..." : "Materialize in Backlog"}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void handleDispatchMaterializedBacklog()}
                  disabled={!canDispatchMaterializedBacklog}
                >
                  {dispatchMaterializedButtonLabel}
                </Button>
                <Button asChild size="sm" variant="outline">
                  <Link href="/backlog?status=all">Open Backlog</Link>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <Link href="/operator">Open Operator</Link>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <Link href="/topology">Open Topology</Link>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <Link href="/subscriptions">Open Subscriptions</Link>
                </Button>
              </div>
              {materializeFeedback ? (
                <p className="text-xs text-muted-foreground">{materializeFeedback}</p>
              ) : null}
              {dispatchFeedback ? (
                <p className="text-xs text-muted-foreground">{dispatchFeedback}</p>
              ) : null}
              {routingPairs.length > 0 ? (
                <div className="border-t pt-4">
                  <p className="page-eyebrow text-[10px]">Recommended lane chain</p>
                  <div className="mt-3 space-y-3">
                    {routingPairs.map((lane) => (
                      <div key={`${lane.task_class}-${lane.preferred_lane}`} className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground">{sentenceCase(lane.task_class)}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {sentenceCase(lane.preferred_lane)} primary, {sentenceCase(lane.overflow_lane)} overflow
                          </p>
                        </div>
                        <Badge variant={lane.degraded ? "secondary" : "outline"} className="shrink-0 text-xs">
                          {lane.degraded ? "degraded" : "ready"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Lane recommendations are not available in the current atlas build.</p>
              )}
            </div>
          </div>

          <div className="surface-instrument rounded-2xl border px-4 py-4">
            <p className="page-eyebrow text-[10px]">Approval posture</p>
            <p className="mt-2 text-sm font-medium text-foreground">
              {nextRequiredApproval?.label ?? "No approval signal available"}
            </p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {nextRequiredApproval?.reason ?? "The master atlas approval surface did not provide a current explanation."}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              {approvalHeldCount > 0
                ? `${approvalHeldCount} approval-held item${approvalHeldCount === 1 ? "" : "s"} remain in the ranked queue.`
                : "No approval-held item is currently leading the ranked queue."}
            </p>
            {nextApprovalActions ? (
              <p className="mt-2 text-xs text-muted-foreground">Allowed now: {nextApprovalActions}</p>
            ) : null}
            {nextRequiredApproval?.allowed_actions?.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {nextRequiredApproval.allowed_actions.slice(0, 4).map((action) => (
                  <Badge key={action} variant="outline" className="text-[10px]">
                    {sentenceCase(action)}
                  </Badge>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </section>

      {sessionLocked ? (
        <div className="surface-panel rounded-[28px] border px-5 py-4 sm:px-6">
          <p className="page-eyebrow">Session Gate</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Routing readouts are partially held until the operator session is active again. Provider posture still refreshes independently.
          </p>
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(20rem,0.95fr)]">
        <section className="space-y-4">
          <div>
            <p className="page-eyebrow">Routing Feed</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Recent decisions</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              The feed should read like an operator ledger: what moved, which policy class governed it, and whether the outcome was clean.
            </p>
          </div>
          <div className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
            {logEntries.length > 0 ? (
              <div className="space-y-3">
                {logEntries.map((entry, index) => (
                  <article
                    key={entry.task_id ?? `${entry.execution_lane ?? "lane"}-${index}`}
                    className="surface-instrument rounded-2xl border px-4 py-4"
                  >
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div className="space-y-1">
                        <p className="page-eyebrow text-[10px]">Task</p>
                        <p className="font-mono text-sm text-foreground">
                          {entry.task_id
                            ? entry.task_id.length > 18
                              ? `${entry.task_id.slice(0, 18)}...`
                              : entry.task_id
                            : "unknown"}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {entry.execution_lane ?? "No lane recorded"} | {entry.provider ?? "No provider recorded"}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant={policyBadgeVariant(entry.policy_class)}>
                          {formatPolicyLabel(entry.policy_class)}
                        </Badge>
                        <Badge variant={outcomeBadgeVariant(entry.outcome)}>
                          {entry.outcome ?? "pending"}
                        </Badge>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No routing data"
                description="Routing decisions will appear here once work is classified and executed."
                className="py-6"
              />
            )}
          </div>
        </section>

        <section className="space-y-4">
          <div className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
            <p className="page-eyebrow">Policy Mix</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Lane posture</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              This is the fast read on how the router is behaving before you open the detailed feed.
            </p>
            <div className="mt-5 space-y-3">
              <div className="surface-instrument flex items-center justify-between rounded-2xl border px-4 py-3">
                <div>
                  <p className="text-sm font-medium">Local-only</p>
                  <p className="text-xs text-muted-foreground">Sovereign, non-escalated work</p>
                </div>
                <Badge variant="outline" className="text-xs">
                  {localOnly}
                </Badge>
              </div>
              <div className="surface-instrument flex items-center justify-between rounded-2xl border px-4 py-3">
                <div>
                  <p className="text-sm font-medium">CLI reviewed</p>
                  <p className="text-xs text-muted-foreground">Human-audited execution path</p>
                </div>
                <Badge variant="secondary" className="text-xs">
                  {cliReviewed}
                </Badge>
              </div>
              <div className="surface-instrument flex items-center justify-between rounded-2xl border px-4 py-3">
                <div>
                  <p className="text-sm font-medium">Cloud escalation</p>
                  <p className="text-xs text-muted-foreground">Premium or fallback lane usage</p>
                </div>
                <Badge variant="destructive" className="text-xs">
                  {cloudEscalation}
                </Badge>
              </div>
            </div>
          </div>

          <div className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
            <p className="page-eyebrow">Provider Lanes</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Active providers</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Providers belong here as operational substrate. Burn posture, leases, and handoffs belong in Subscriptions.
            </p>
            <div className="mt-5 space-y-2">
              {providers.length > 0 ? (
                providers.map((provider) => (
                  <div
                    key={provider.id ?? provider.name}
                    className="surface-instrument flex items-center gap-4 rounded-2xl border px-4 py-3"
                  >
                    <div className={`h-2.5 w-2.5 shrink-0 rounded-full ${statusDot(provider.status)}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-medium">{provider.name}</p>
                        {provider.execution_mode ? (
                          <Badge variant="outline" className="text-xs">
                            {provider.execution_mode}
                          </Badge>
                        ) : null}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {provider.tasks_today != null ? `${provider.tasks_today} tasks today` : "No task sample"} |{" "}
                        {provider.avg_latency_ms != null ? `${provider.avg_latency_ms}ms avg latency` : "Latency unavailable"}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState
                  title="No provider data"
                  description="Provider posture will appear here when the routing registry has a live provider sample."
                  className="py-6"
                />
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}


