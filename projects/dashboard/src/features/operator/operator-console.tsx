"use client";

import Link from "next/link";
import { useCallback, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Inbox,
  LoaderCircle,
  MessageSquare,
  RefreshCcw,
  Send,
  ShieldCheck,
  Square,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { RichText } from "@/components/rich-text";
import { PilotReadinessBlock } from "@/components/pilot-readiness-block";
import { StatCard } from "@/components/stat-card";
import { requestJson, postWithoutBody, postJson } from "@/features/workforce/helpers";
import type {
  BuilderFrontDoorSummary,
  ExecutionReviewProjection,
  SteadyStateSnapshot,
} from "@/lib/contracts";
import { formatRelativeTime } from "@/lib/format";
import type { MasterAtlasRelationshipMap } from "@/lib/master-atlas";
import type { BlockerMap } from "@/lib/blocker-map";
import type { BlockerExecutionPlan } from "@/lib/blocker-execution-plan";
import type { ContinuityControllerState } from "@/lib/continuity-controller";
import { buildSteadyStateDecisionSummary } from "@/lib/steady-state-summary";
import { readChatEventStream } from "@/lib/sse";
import type { AutonomousValueProof } from "@/lib/autonomous-value-proof";
import type { ProjectFactoryConsoleSnapshot } from "@/lib/project-factory";
import type { ValueThroughputScorecard } from "@/lib/value-throughput";
import {
  getBuilderKernelPressureLabel,
  getBuilderKernelSharedPressure,
  getBuilderKernelPressureTone,
} from "@/lib/builder-kernel-pressure";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

interface OperatorReadStatus {
  available?: boolean;
  degraded?: boolean;
  detail?: string;
  source?: string;
}

export interface PendingApprovalsPayload extends OperatorReadStatus {
  reviews?: ExecutionReviewProjection[];
  count?: number;
}

export interface GovernanceSnapshot {
  available?: boolean;
  degraded?: boolean;
  detail?: string;
  source?: string;
  current_mode?: {
    mode?: string;
    entered_at?: number;
    trigger?: string;
  };
  launch_blockers?: string[];
  launch_ready?: boolean;
  attention_posture?: {
    recommended_mode?: string;
    breaches?: string[];
  };
}

interface TaskResidueSummary {
  total?: number;
  pending_approval?: number;
  stale_lease?: number;
  stale_lease_actionable?: number;
  stale_lease_recovered_historical?: number;
  failed_actionable?: number;
  failed_historical_repaired?: number;
}

export interface OperatorSummaryPayload {
  available?: boolean;
  degraded?: boolean;
  detail?: string;
  source?: string;
  blockerMap?: BlockerMap | null;
  blockerMapStatus?: {
    available?: boolean;
    degraded?: boolean;
    detail?: string | null;
    sourceKind?: "workspace_report" | "repo_root_fallback" | null;
    sourcePath?: string | null;
  } | null;
  blockerExecutionPlan?: BlockerExecutionPlan | null;
  blockerExecutionPlanStatus?: {
    available?: boolean;
    degraded?: boolean;
    detail?: string | null;
    sourceKind?: "workspace_report" | "repo_root_fallback" | null;
    sourcePath?: string | null;
  } | null;
  continuityController?: ContinuityControllerState | null;
  continuityControllerStatus?: {
    available?: boolean;
    degraded?: boolean;
    detail?: string | null;
    sourceKind?: "workspace_report" | "repo_root_fallback" | null;
    sourcePath?: string | null;
  } | null;
  scheduled?: {
    totalJobs?: number;
    queueBackedJobs?: number;
    directJobs?: number;
    proposalOnlyJobs?: number;
    blockedJobs?: number;
    needsSyncJobs?: number;
  };
  valueThroughput?: ValueThroughputScorecard | null;
  valueThroughputStatus?: {
    available?: boolean;
    degraded?: boolean;
    detail?: string | null;
    sourceKind?: "workspace_report" | "repo_root_fallback" | null;
    sourcePath?: string | null;
  } | null;
  autonomousValueProof?: AutonomousValueProof | null;
  autonomousValueProofStatus?: {
    available?: boolean;
    degraded?: boolean;
    detail?: string | null;
    sourceKind?: "workspace_report" | "repo_root_fallback" | null;
    sourcePath?: string | null;
  } | null;
  tasks?: TaskResidueSummary;
  steadyState?: SteadyStateSnapshot | null;
  builderFrontDoor?: BuilderFrontDoorSummary | null;
  steadyStateStatus?: {
    available?: boolean;
    degraded?: boolean;
    detail?: string | null;
    sourceKind?: "workspace_report" | "repo_root_fallback" | null;
    sourcePath?: string | null;
  } | null;
  projectFactory?: {
    acceptedProjectOutputCount?: number;
    broadProjectFactoryReady?: boolean;
    factoryOperatingMode?: string;
    latestPendingProjectId?: string | null;
    pendingCandidateCount?: number;
    pendingHybridAcceptanceCount?: number;
    projectOutputStageMet?: boolean;
    topPriorityProjectId?: string | null;
    topPriorityProjectLabel?: string | null;
  } | null;
  projectFactoryStatus?: {
    available?: boolean;
    degraded?: boolean;
    detail?: string | null;
    sourceKind?: "workspace_report" | "repo_root_fallback" | null;
    sourcePath?: string | null;
  } | null;
}

function createId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function formatHours(value: number) {
  return Number.isInteger(value) ? `${value}` : value.toFixed(1).replace(/\.0$/, "");
}

function OperatorMetric({
  label,
  value,
  detail,
  tone = "default",
}: {
  label: string;
  value: string;
  detail: string;
  tone?: "default" | "success" | "warning";
}) {
  const toneClass =
    tone === "success"
      ? "text-[color:var(--signal-success)]"
      : tone === "warning"
        ? "text-[color:var(--signal-warning)]"
        : "text-foreground";

  return (
    <div className="surface-metric rounded-2xl border px-4 py-3">
      <p className="page-eyebrow text-[10px]">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tracking-tight ${toneClass}`}>{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

const SUGGESTED_PROMPTS = [
  "What needs my attention?",
  "Show me today's plans",
  "What did agents do overnight?",
];

const PENDING_APPROVALS_KEY = ["operator-pending-approvals"] as const;
const GOVERNANCE_KEY = ["operator-governance"] as const;
const SUMMARY_KEY = ["operator-summary"] as const;
const MASTER_ATLAS_KEY = ["operator-master-atlas"] as const;
const PROJECT_FACTORY_KEY = ["operator-project-factory"] as const;

export interface OperatorConsoleInitialData {
  pendingApprovals: PendingApprovalsPayload;
  governance: GovernanceSnapshot;
  operatorSummary: OperatorSummaryPayload;
  masterAtlas: MasterAtlasRelationshipMap | null;
  projectFactory: ProjectFactoryConsoleSnapshot | null;
}

export function OperatorConsole({ initialData = null }: { initialData?: OperatorConsoleInitialData | null }) {
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const pendingApprovalsQuery = useQuery({
    queryKey: PENDING_APPROVALS_KEY,
    queryFn: async (): Promise<PendingApprovalsPayload> => {
      const data = await requestJson("/api/execution/reviews?status=pending");
      return (data ?? {}) as PendingApprovalsPayload;
    },
    initialData: initialData?.pendingApprovals,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const governanceQuery = useQuery({
    queryKey: GOVERNANCE_KEY,
    queryFn: async (): Promise<GovernanceSnapshot> => {
      const data = await requestJson("/api/operator/governance");
      return (data ?? {}) as GovernanceSnapshot;
    },
    initialData: initialData?.governance,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const summaryQuery = useQuery({
    queryKey: SUMMARY_KEY,
    queryFn: async (): Promise<OperatorSummaryPayload> => {
      const data = await requestJson("/api/operator/summary");
      return (data ?? {}) as OperatorSummaryPayload;
    },
    initialData: initialData?.operatorSummary,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const masterAtlasQuery = useQuery({
    queryKey: MASTER_ATLAS_KEY,
    queryFn: async (): Promise<MasterAtlasRelationshipMap> => {
      const data = await requestJson("/api/master-atlas");
      return (data ?? {}) as MasterAtlasRelationshipMap;
    },
    initialData: initialData?.masterAtlas ?? undefined,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
  const projectFactoryQuery = useQuery({
    queryKey: PROJECT_FACTORY_KEY,
    queryFn: async (): Promise<ProjectFactoryConsoleSnapshot> => {
      const data = await requestJson("/api/projects/factory");
      return (data ?? {}) as ProjectFactoryConsoleSnapshot;
    },
    initialData: initialData?.projectFactory ?? undefined,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const pendingApprovalsPayload = pendingApprovalsQuery.data ?? {};
  const pendingApprovals = pendingApprovalsPayload.reviews ?? [];
  const governance = governanceQuery.data ?? {};
  const operatorSummary = summaryQuery.data ?? {};
  const taskResidue = operatorSummary.tasks ?? {};
  const scheduled = operatorSummary.scheduled ?? {};
  const steadyState = operatorSummary.steadyState ?? null;
  const builderFrontDoor = operatorSummary.builderFrontDoor ?? null;
  const blockerMap = operatorSummary.blockerMap ?? null;
  const blockerExecutionPlan = operatorSummary.blockerExecutionPlan ?? null;
  const continuityController = operatorSummary.continuityController ?? null;
  const valueThroughput = operatorSummary.valueThroughput ?? null;
  const autonomousValueProof = operatorSummary.autonomousValueProof ?? null;
  const projectFactory = operatorSummary.projectFactory ?? null;
  const builderCurrent = builderFrontDoor?.current_session ?? null;
  const blockerMapStatus = operatorSummary.blockerMapStatus ?? null;
  const blockerExecutionPlanStatus = operatorSummary.blockerExecutionPlanStatus ?? null;
  const continuityControllerStatus = operatorSummary.continuityControllerStatus ?? null;
  const steadyStateStatus = operatorSummary.steadyStateStatus ?? null;
  const valueThroughputStatus = operatorSummary.valueThroughputStatus ?? null;
  const autonomousValueProofStatus = operatorSummary.autonomousValueProofStatus ?? null;
  const projectFactoryStatus = operatorSummary.projectFactoryStatus ?? null;
  const masterAtlas =
    masterAtlasQuery.data && typeof masterAtlasQuery.data.generated_at === "string"
      ? masterAtlasQuery.data
      : null;
  const masterAtlasSummary = masterAtlas?.summary ?? null;
  const gooseEvidence = masterAtlas?.goose_evidence_summary ?? null;
  const projectFactorySnapshot = projectFactoryQuery.data ?? null;
  const latestPendingProjectCandidate = projectFactorySnapshot?.latestPendingCandidate ?? null;
  const approvalsAvailable = pendingApprovalsPayload.available !== false;
  const governanceAvailable = governance.available !== false;
  const summaryAvailable = summaryQuery.data?.available !== false;
  const operatorFeedAvailable = approvalsAvailable && governanceAvailable && summaryAvailable;
  const currentMode = governance.current_mode?.mode ?? "unknown";
  const launchBlockers = governance.launch_blockers ?? [];
  const attentionBreaches = governance.attention_posture?.breaches ?? [];
  const approvalHeldTasks = Number(taskResidue.pending_approval ?? 0);
  const actionableFailures = Number(taskResidue.failed_actionable ?? 0);
  const staleLeases = Number(taskResidue.stale_lease_actionable ?? taskResidue.stale_lease ?? 0);
  const recoveredStaleLeases = Number(taskResidue.stale_lease_recovered_historical ?? 0);
  const repairedHistorical = Number(taskResidue.failed_historical_repaired ?? 0);
  const scheduledQueueBackedJobs = Number(scheduled.queueBackedJobs ?? 0);
  const scheduledDirectJobs = Number(scheduled.directJobs ?? 0);
  const scheduledProposalOnlyJobs = Number(scheduled.proposalOnlyJobs ?? 0);
  const scheduledBlockedJobs = Number(scheduled.blockedJobs ?? 0);
  const scheduledNeedsSyncJobs = Number(scheduled.needsSyncJobs ?? 0);
  const blockerMapAvailable = Boolean(blockerMap);
  const remainingBlockerFamilies = Number(blockerMap?.remaining.familyCount ?? 0);
  const remainingBlockerPaths = Number(blockerMap?.remaining.pathCount ?? 0);
  const nextTrancheTitle = blockerMap?.nextTranche.title ?? blockerMap?.nextTranche.id ?? "No tranche queued";
  const nextTranchePaths = Number(blockerMap?.nextTranche.matchCount ?? 0);
  const proofGateStatus = blockerMap?.proofGate.status ?? "unknown";
  const autoMutationState = blockerMap?.autoMutation.state ?? "unknown";
  const stableDayCoveredHours = Number(blockerMap?.stableOperatingDay.coveredWindowHours ?? 0);
  const stableDayRequiredHours = Number(blockerMap?.stableOperatingDay.requiredWindowHours ?? 24);
  const stableDayMet = Boolean(blockerMap?.stableOperatingDay.met);
  const resultEvidenceThresholdProgress = Number(blockerMap?.resultEvidence.thresholdProgress ?? 0);
  const resultEvidenceThresholdRequired = Number(blockerMap?.resultEvidence.thresholdRequired ?? 5);
  const resultEvidenceThresholdMet = Boolean(blockerMap?.resultEvidence.thresholdMet);
  const proofProgressSummary = blockerMapAvailable
    ? `stable day ${
        stableDayMet
          ? `met (${formatHours(stableDayCoveredHours)}/${formatHours(stableDayRequiredHours)}h)`
          : `${formatHours(stableDayCoveredHours)}/${formatHours(stableDayRequiredHours)}h`
      } · result evidence ${
        resultEvidenceThresholdMet
          ? `met (${resultEvidenceThresholdProgress}/${resultEvidenceThresholdRequired})`
          : `${resultEvidenceThresholdProgress}/${resultEvidenceThresholdRequired}`
      }`
    : "Proof progress unavailable";
  const continuityStatus = continuityController?.controllerStatus ?? "unknown";
  const continuityActiveFamily =
    continuityController?.activeSubtrancheId ??
    continuityController?.activeFamilyId ??
    blockerExecutionPlan?.nextTarget.subtrancheId ??
    blockerExecutionPlan?.nextTarget.familyId ??
    "none";
  const continuityNextTarget =
    continuityController?.nextTarget?.subtrancheTitle ??
    continuityController?.nextTarget?.familyTitle ??
    blockerExecutionPlan?.nextTarget.subtrancheTitle ??
    blockerExecutionPlan?.nextTarget.familyTitle ??
    nextTrancheTitle;
  const continuitySkipReason = continuityController?.lastSkipReason ?? "none";
  const continuityBackoff = continuityController?.backoffUntil ?? "none";
  const continuitySummary = continuityController
    ? `${continuityActiveFamily} active/selected · next ${continuityNextTarget} · skip ${continuitySkipReason} · backoff ${continuityBackoff}`
    : continuityControllerStatus?.detail ??
      blockerExecutionPlanStatus?.detail ??
      "Continuity controller artifacts are temporarily unavailable.";
  const blockerMapSummary = blockerMapAvailable
    ? `${remainingBlockerFamilies} family tranche${remainingBlockerFamilies === 1 ? "" : "s"} / ${remainingBlockerPaths} path match${remainingBlockerPaths === 1 ? "" : "es"}`
    : blockerMapStatus?.detail ?? "Canonical blocker map is temporarily unavailable.";
  const blockerMapDetail = blockerMapAvailable
    ? `Next: ${nextTrancheTitle} (${nextTranchePaths} path${nextTranchePaths === 1 ? "" : "s"}) · proof gate ${proofGateStatus} · ${proofProgressSummary} · auto-mutation ${autoMutationState}`
    : blockerMapStatus?.detail ?? "Canonical blocker map is temporarily unavailable.";
  const resultBackedCompletions = Number(valueThroughput?.resultBackedCompletionCount ?? 0);
  const reviewBackedOutputs = Number(valueThroughput?.reviewBackedOutputCount ?? 0);
  const staleClaimCount = Number(valueThroughput?.staleClaimCount ?? 0);
  const reviewDebtCount = Number(valueThroughput?.reviewDebt.count ?? 0);
  const reviewDebtAge = Number(valueThroughput?.reviewDebt.oldestAgeHours ?? 0);
  const directControlLoops = Number(valueThroughput?.scheduledExecution.directControlJobs ?? 0);
  const proposalOnlyLoops = Number(valueThroughput?.scheduledExecution.proposalOnlyJobs ?? 0);
  const reconciliationIssueCount = Number(valueThroughput?.reconciliation.issueCount ?? 0);
  const valueThroughputAvailable = Boolean(valueThroughput);
  const valueThroughputDegraded = Boolean(valueThroughputStatus?.degraded);
  const valueThroughputSummary = valueThroughputAvailable
    ? `${resultBackedCompletions} result-backed · ${reviewBackedOutputs} review-backed · ${staleClaimCount} stale claim${staleClaimCount === 1 ? "" : "s"} · ${reviewDebtCount} review debt · ${directControlLoops} direct-control · ${proposalOnlyLoops} proposal-only`
    : valueThroughputStatus?.detail ?? "Value-throughput scorecard is temporarily unavailable.";
  const valueThroughputDetail = valueThroughputDegraded && valueThroughputStatus?.detail
    ? `${valueThroughputSummary} · ${valueThroughputStatus.detail}`
    : valueThroughputSummary;
  const autonomousValueAvailable = Boolean(autonomousValueProof);
  const autonomousValueDegraded = Boolean(autonomousValueProofStatus?.degraded);
  const acceptedOperatorValueCount = Number(autonomousValueProof?.acceptedOperatorValueCount ?? 0);
  const acceptedProductValueCount = Number(autonomousValueProof?.acceptedProductValueCount ?? 0);
  const disqualifiedValueCount = Number(autonomousValueProof?.disqualifiedEntryCount ?? 0);
  const latestAcceptedTitle = autonomousValueProof?.latestAcceptedEntry?.title ?? "No accepted autonomous value proof";
  const latestAcceptedSurface = autonomousValueProof?.latestAcceptedEntry?.beneficiarySurface ?? "unscoped";
  const latestAcceptedKind = autonomousValueProof?.latestAcceptedEntry?.deliverableKind ?? "unknown";
  const operatorValueStageMet = Boolean(autonomousValueProof?.stageStatus.operatorValue.met);
  const productValueStageMet = Boolean(autonomousValueProof?.stageStatus.productValue.met);
  const remainingOperatorValue = Number(autonomousValueProof?.stageStatus.operatorValue.remainingRequired ?? 0);
  const remainingProductValue = Number(autonomousValueProof?.stageStatus.productValue.remainingRequired ?? 0);
  const autonomousValueSummary = autonomousValueAvailable
    ? `${acceptedOperatorValueCount} operator-value · ${acceptedProductValueCount} product-value · ${disqualifiedValueCount} disqualified`
    : autonomousValueProofStatus?.detail ?? "Autonomous value proof is temporarily unavailable.";
  const autonomousValueDetail =
    autonomousValueDegraded && autonomousValueProofStatus?.detail
      ? `${autonomousValueSummary} · ${autonomousValueProofStatus.detail}`
      : autonomousValueSummary;
  const autonomousValueTone =
    !autonomousValueAvailable || autonomousValueDegraded || disqualifiedValueCount > 0
      ? "warning"
      : acceptedOperatorValueCount > 0 || acceptedProductValueCount > 0
        ? "success"
        : "default";
  const projectFactoryMode =
    projectFactory?.factoryOperatingMode ?? masterAtlasSummary?.project_factory_operating_mode ?? "unknown";
  const projectFactoryTopProjectId =
    projectFactory?.topPriorityProjectId ?? masterAtlasSummary?.project_factory_top_priority_project_id ?? "none";
  const projectFactoryTopProjectLabel =
    projectFactory?.topPriorityProjectLabel ??
    masterAtlasSummary?.project_factory_top_priority_project_label ??
    projectFactoryTopProjectId;
  const projectFactoryAcceptedCount = Number(
    projectFactory?.acceptedProjectOutputCount ?? masterAtlasSummary?.accepted_project_output_count ?? 0,
  );
  const projectFactoryPendingCandidateCount = Number(
    projectFactory?.pendingCandidateCount ?? masterAtlasSummary?.pending_project_output_candidate_count ?? 0,
  );
  const projectFactoryPendingHybridCount = Number(
    projectFactory?.pendingHybridAcceptanceCount ?? masterAtlasSummary?.pending_hybrid_project_output_count ?? 0,
  );
  const projectFactoryLatestPendingProjectId =
    projectFactory?.latestPendingProjectId ??
    masterAtlasSummary?.project_factory_latest_pending_project_id ??
    "none";
  const projectFactoryBroadReady = Boolean(
    projectFactory?.broadProjectFactoryReady ?? masterAtlasSummary?.project_factory_broad_ready,
  );
  const projectOutputStageMet = Boolean(
    projectFactory?.projectOutputStageMet ?? masterAtlasSummary?.project_output_stage_met,
  );
  const projectFactorySummary = `${projectFactoryAcceptedCount} accepted · ${projectFactoryPendingCandidateCount} pending candidate${projectFactoryPendingCandidateCount === 1 ? "" : "s"} · ${projectFactoryPendingHybridCount} hybrid review`;
  const projectFactoryDetail = `Top ${projectFactoryTopProjectLabel} · latest pending ${projectFactoryLatestPendingProjectId} · mode ${projectFactoryMode}`;
  const projectFactoryTone =
    projectOutputStageMet && projectFactoryBroadReady
      ? "success"
      : projectFactoryPendingCandidateCount > 0 || projectFactoryPendingHybridCount > 0
        ? "warning"
        : "default";
  const masterAtlasDegraded =
    !masterAtlas ||
    masterAtlas.available === false ||
    Boolean(masterAtlas.degraded) ||
    Boolean(masterAtlas.error);
  const masterAtlasDetail =
    masterAtlas?.detail ??
    masterAtlas?.error ??
    "Routing and topology own the wider dispatch and capacity context for this system.";
  const governedDispatch = masterAtlas?.governed_dispatch_execution ?? null;
  const steadyStateSummary = buildSteadyStateDecisionSummary(steadyState, {
    attentionLabel: governanceAvailable ? currentMode : "feed offline",
    attentionSummary: !governanceAvailable
      ? "Governance posture feed is temporarily unavailable."
      : governance.attention_posture?.recommended_mode
        ? `Recommended: ${governance.attention_posture.recommended_mode}`
        : "No alternate mode recommendation is active right now.",
    currentWorkTitle: governedDispatch?.current_task_title ?? "No governed work published.",
    currentWorkDetail: governedDispatch?.dispatch_outcome ?? "No current provider or lane published.",
    nextUpTitle: masterAtlas?.turnover_readiness?.top_dispatchable_autonomous_task_title ?? "No follow-on handoff published.",
    nextUpDetail:
      masterAtlas?.turnover_readiness?.dispatchable_autonomous_queue_count != null
        ? `${masterAtlas.turnover_readiness.dispatchable_autonomous_queue_count} dispatchable lane(s) remain.`
        : "No next operator action published.",
    queuePosture: `${approvalHeldTasks} approvals / ${staleLeases} stale leases / ${actionableFailures} failures / ${scheduledQueueBackedJobs} queued / ${scheduledProposalOnlyJobs} proposal-only`,
    needsYou: approvalHeldTasks > 0 || actionableFailures > 0 || launchBlockers.length > 0 || scheduledNeedsSyncJobs > 0,
  });
  const operatorNeedsYou = steadyStateSummary.needsYou;
  const operatorAttentionLabel = steadyStateSummary.attentionLabel;
  const operatorAttentionSummary = steadyStateSummary.attentionSummary;
  const operatorCurrentWork = steadyStateSummary.currentWorkTitle;
  const operatorCurrentWorkDetail = steadyStateSummary.currentWorkDetail;
  const operatorNextUp = steadyStateSummary.nextUpTitle;
  const operatorNextUpDetail = steadyStateSummary.nextUpDetail;
  const builderSharedPressure = builderFrontDoor ? getBuilderKernelSharedPressure(builderFrontDoor) : null;
  const builderPressureLabel = builderFrontDoor ? getBuilderKernelPressureLabel(builderFrontDoor) : "offline";
  const builderNeedsSync = builderSharedPressure?.current_session_needs_sync ?? false;
  const builderSharedReviewCount = builderSharedPressure?.current_session_pending_review_count ?? 0;
  const builderSharedResultCount = builderSharedPressure?.current_session_actionable_result_count ?? 0;
  const builderAttentionTone = !builderFrontDoor
    ? "warning"
    : getBuilderKernelPressureTone(builderFrontDoor) === "danger"
      ? "warning"
      : getBuilderKernelPressureTone(builderFrontDoor) === "warning"
        ? "warning"
        : "success";
  const valueThroughputTone =
    !valueThroughputAvailable || valueThroughputDegraded || staleClaimCount > 0 || reconciliationIssueCount > 0
      ? "warning"
      : resultBackedCompletions > 0 || reviewBackedOutputs > 0
        ? "success"
        : "default";
  const governedDispatchHealthy =
    Boolean(governedDispatch) &&
    !governedDispatch?.error &&
    (governedDispatch?.task_status === "running" ||
      governedDispatch?.backlog_status === "scheduled" ||
      governedDispatch?.status === "already_dispatched" ||
      governedDispatch?.status === "dispatched");
  const gooseEvidenceEvalSummary = gooseEvidence
    ? [
        gooseEvidence.formal_eval_status ? `formal eval ${gooseEvidence.formal_eval_status}` : null,
        gooseEvidence.formal_eval_successes != null || gooseEvidence.formal_eval_failures != null
          ? `${gooseEvidence.formal_eval_successes ?? 0} passed / ${gooseEvidence.formal_eval_failures ?? 0} failed`
          : null,
        gooseEvidence.command_available_locally === true
          ? `${gooseEvidence.command ?? "goose"} available locally`
          : gooseEvidence.command_available_locally === false
            ? `${gooseEvidence.command ?? "goose"} unavailable locally`
            : null,
      ]
      .filter((value): value is string => typeof value === "string")
      .join(" · ")
    : null;
  const gooseEvidencePacketSummary = gooseEvidence
    ? [
        gooseEvidence.packet_status ? `packet ${gooseEvidence.packet_status}` : null,
        gooseEvidence.approval_state ? `approval ${gooseEvidence.approval_state}` : null,
        gooseEvidence.proof_state ? `proof ${gooseEvidence.proof_state}` : null,
      ]
        .filter((value): value is string => typeof value === "string")
        .join(" · ")
    : null;

  const approveMutation = useMutation({
    mutationFn: async (approvalId: string) => {
      await postWithoutBody(`/api/execution/reviews/${encodeURIComponent(approvalId)}/approve`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PENDING_APPROVALS_KEY });
      void queryClient.invalidateQueries({ queryKey: GOVERNANCE_KEY });
      void queryClient.invalidateQueries({ queryKey: SUMMARY_KEY });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async ({ approvalId, reason }: { approvalId: string; reason: string }) => {
      await postJson(`/api/execution/reviews/${encodeURIComponent(approvalId)}/reject`, { reason });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PENDING_APPROVALS_KEY });
      void queryClient.invalidateQueries({ queryKey: GOVERNANCE_KEY });
      void queryClient.invalidateQueries({ queryKey: SUMMARY_KEY });
    },
  });

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    });
  }, []);

  async function sendMessage(promptOverride?: string) {
    const content = (promptOverride ?? input).trim();
    if (!content || isStreaming) return;

    const userMsg: ChatMessage = {
      id: createId("msg"),
      role: "user",
      content,
      createdAt: new Date().toISOString(),
    };

    const assistantMsg: ChatMessage = {
      id: createId("msg"),
      role: "assistant",
      content: "",
      createdAt: new Date().toISOString(),
    };

    const allMessages = [...messages, userMsg];

    setMessages([...allMessages, assistantMsg]);
    setInput("");
    setError(null);
    setIsStreaming(true);
    scrollToBottom();

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: "agent-server",
          model: "meta-orchestrator",
          messages: allMessages.map((message) => ({ role: message.role, content: message.content })),
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Request failed (${response.status})`);
      }

      let assistantContent = "";
      await readChatEventStream(response.body, (event) => {
        if (event.type === "assistant_delta") {
          assistantContent += event.content;
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantMsg.id ? { ...message, content: assistantContent } : message,
            ),
          );
          scrollToBottom();
        }

        if (event.type === "error") {
          setError(event.message);
        }
      });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setError("Stopped.");
      } else {
        setError(err instanceof Error ? err.message : "Request failed.");
      }
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Command Center"
        title="Operator Console"
        description="Approvals, governance posture, and operator chat. This page should feel like the command desk, not a secondary dashboard."
        attentionHref="/operator"
        actions={
          <Button
            variant="outline"
            onClick={() => {
              void pendingApprovalsQuery.refetch();
              void governanceQuery.refetch();
              void summaryQuery.refetch();
              void masterAtlasQuery.refetch();
              void projectFactoryQuery.refetch();
            }}
            disabled={
              pendingApprovalsQuery.isFetching ||
              governanceQuery.isFetching ||
              summaryQuery.isFetching ||
              masterAtlasQuery.isFetching ||
              projectFactoryQuery.isFetching
            }
          >
            <RefreshCcw
              className={`mr-2 h-4 w-4 ${
                pendingApprovalsQuery.isFetching ||
                governanceQuery.isFetching ||
                summaryQuery.isFetching ||
                masterAtlasQuery.isFetching ||
                projectFactoryQuery.isFetching
                  ? "animate-spin"
                  : ""
              }`}
            />
            Refresh
          </Button>
        }
      >
        {!operatorFeedAvailable ? (
          <div className="surface-panel mt-5 rounded-[24px] border border-[color:var(--signal-warning)]/40 px-5 py-4 sm:px-6">
            <p className="page-eyebrow text-[color:var(--signal-warning)]">Operator data degraded</p>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-muted-foreground">
              The dashboard runtime cannot currently reach the upstream operator feed from this node. The command lane is still available, but approvals, governance posture, and residue metrics may be incomplete until the agent-server path is restored.
            </p>
          </div>
        ) : null}

        {steadyStateStatus?.degraded ? (
          <div className="surface-panel mt-5 rounded-[24px] border border-[color:var(--signal-warning)]/40 px-5 py-4 sm:px-6">
            <p className="page-eyebrow text-[color:var(--signal-warning)]">Steady-state front door degraded</p>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-muted-foreground">
              {steadyStateStatus.detail ?? "The steady-state front door is unavailable from this dashboard runtime."}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Source: {steadyStateStatus.sourceKind ?? "unknown"}
              {steadyStateStatus.sourcePath ? ` · ${steadyStateStatus.sourcePath}` : ""}
            </p>
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-8">
          <StatCard
            label="Actionable Failures"
            value={summaryAvailable ? `${actionableFailures}` : "offline"}
            detail={
              !summaryAvailable
                ? "Operator summary feed is temporarily unavailable."
                    : repairedHistorical > 0 || recoveredStaleLeases > 0 || staleLeases > 0
                      ? `${repairedHistorical} repaired failures / ${recoveredStaleLeases} recovered stale leases / ${staleLeases} live stale leases`
                      : "No repaired residue or live stale leases recorded."
            }
            icon={<MessageSquare className="h-5 w-5" />}
            tone={!summaryAvailable || actionableFailures > 0 ? "warning" : "success"}
          />
          <StatCard
            label="Approval-Held Tasks"
            value={approvalsAvailable ? `${approvalHeldTasks}` : "offline"}
            detail={
              approvalsAvailable
                ? `${pendingApprovals.length} approval request record${pendingApprovals.length === 1 ? "" : "s"}.`
                : "Approval queue feed is temporarily unavailable."
            }
            icon={<Inbox className="h-5 w-5" />}
            tone={!approvalsAvailable || approvalHeldTasks > 0 ? "warning" : "success"}
          />
          <StatCard
            label="Operator Attention"
            value={summaryAvailable ? operatorAttentionLabel : "offline"}
            detail={
              summaryAvailable
                ? operatorAttentionSummary
                : "Operator summary feed is temporarily unavailable."
            }
            icon={<ShieldCheck className="h-5 w-5" />}
            tone={!summaryAvailable || operatorNeedsYou ? "warning" : "success"}
          />
          <StatCard
            label="Current Work"
            value={summaryAvailable ? operatorCurrentWork : "offline"}
            detail={
              summaryAvailable ? `${operatorCurrentWorkDetail} Next: ${operatorNextUp}` : "Operator summary feed is temporarily unavailable."
            }
            icon={<MessageSquare className="h-5 w-5" />}
            tone={summaryAvailable && steadyState?.currentWork?.taskTitle ? "success" : "warning"}
          />
          <StatCard
            label="Closure blockers"
            value={blockerMapAvailable ? `${remainingBlockerFamilies}` : "offline"}
            detail={blockerMapAvailable ? blockerMapDetail : blockerMapSummary}
            icon={<AlertTriangle className="h-5 w-5" />}
            tone={!blockerMapAvailable || remainingBlockerFamilies > 0 ? "warning" : "success"}
          />
          <StatCard
            label="Continuity controller"
            value={continuityController ? continuityStatus : "offline"}
            detail={continuitySummary}
            icon={<LoaderCircle className="h-5 w-5" />}
            tone={
              !continuityController ||
              continuityControllerStatus?.degraded ||
              continuityStatus === "blocked" ||
              continuityStatus === "skipped"
                ? "warning"
                : "success"
            }
          />
          <StatCard
            label="Scheduled queue"
            value={summaryAvailable ? `${scheduledQueueBackedJobs}` : "offline"}
            detail={
              summaryAvailable
                ? `${scheduledProposalOnlyJobs} proposal-only · ${scheduledDirectJobs} direct loop · ${scheduledBlockedJobs} blocked · ${scheduledNeedsSyncJobs} need sync`
                : "Operator summary feed is temporarily unavailable."
            }
            icon={<RefreshCcw className="h-5 w-5" />}
            tone={!summaryAvailable || scheduledNeedsSyncJobs > 0 || scheduledBlockedJobs > 0 ? "warning" : "success"}
          />
          <StatCard
            label="Value throughput"
            value={valueThroughputAvailable ? `${resultBackedCompletions}` : "offline"}
            detail={valueThroughputDetail}
            icon={<BarChart3 className="h-5 w-5" />}
            tone={valueThroughputTone}
          />
          <StatCard
            label="Autonomous value"
            value={autonomousValueAvailable ? `${acceptedOperatorValueCount}/${acceptedProductValueCount}` : "offline"}
            detail={autonomousValueDetail}
            icon={<BarChart3 className="h-5 w-5" />}
            tone={autonomousValueTone}
          />
          <StatCard
            label="Builder Kernel"
            value={builderPressureLabel}
            detail={
              builderFrontDoor
                ? builderCurrent
                  ? builderNeedsSync
                    ? `${builderCurrent.primary_adapter} · shared review/result evidence missing`
                    : `${builderCurrent.primary_adapter} · ${builderSharedReviewCount} shared review(s) · ${builderSharedResultCount} result alert(s)`
                  : "No active builder session published."
                : "Builder front door is not attached to the operator summary route."
            }
            icon={<ShieldCheck className="h-5 w-5" />}
            tone={builderAttentionTone}
          />
          <StatCard
            label="Project Factory"
            value={projectFactoryTopProjectLabel}
            detail={projectFactoryDetail}
            icon={<BarChart3 className="h-5 w-5" />}
            tone={projectFactoryTone}
          />
          <StatCard
            label="Project Outputs"
            value={`${projectFactoryAcceptedCount}/${projectFactoryPendingCandidateCount}`}
            detail={projectFactorySummary}
            icon={<Inbox className="h-5 w-5" />}
            tone={projectFactoryTone}
          />
        </div>
      </PageHeader>

      <PilotReadinessBlock />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(21rem,0.85fr)]">
        <section className="space-y-4">
          <div>
            <p className="page-eyebrow">Approval Desk</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Decision queue</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              This is the operator-first lane: pending approvals, launch blockers, and the residue that still needs a human decision.
            </p>
          </div>

          <div className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
            <div className="grid gap-3 md:grid-cols-3">
              <OperatorMetric
                label="Attention"
                value={operatorAttentionLabel}
                detail={
                  steadyState?.nextOperatorAction ??
                  (governance.current_mode?.trigger
                    ? `Entered via ${governance.current_mode.trigger}`
                    : "No explicit next operator action recorded")
                }
                tone={operatorNeedsYou ? "warning" : "success"}
              />
              <OperatorMetric
                label="Launch blockers"
                value={`${launchBlockers.length}`}
                detail={governance.launch_ready ? "Launch posture is clear" : "Promotion still blocked"}
                tone={launchBlockers.length > 0 ? "warning" : "success"}
              />
              <OperatorMetric
                label="Next tranche"
                value={blockerMapAvailable ? `${remainingBlockerFamilies}` : "offline"}
                detail={blockerMapDetail}
                tone={!blockerMapAvailable || remainingBlockerFamilies > 0 ? "warning" : "success"}
              />
              <OperatorMetric
                label="Current work"
                value={operatorCurrentWork}
                detail={`${operatorCurrentWorkDetail} Next: ${operatorNextUp}`}
                tone={steadyState?.currentWork?.taskTitle ? "success" : "warning"}
              />
              <OperatorMetric
                label="Project factory"
                value={projectFactoryTopProjectLabel}
                detail={`${projectFactorySummary} · ${projectFactoryDetail}`}
                tone={projectFactoryTone === "success" ? "success" : "warning"}
              />
            </div>

            <div className="mt-5 space-y-3">
              {!approvalsAvailable ? (
                <EmptyState
                  title="Approval feed unavailable"
                  description="The dashboard cannot currently read the live approval queue from the operator upstream."
                  className="py-6"
                />
              ) : pendingApprovals.length > 0 ? (
                pendingApprovals.map((approval) => {
                  const summary = approval.task_prompt || approval.reason;
                  return (
                    <article
                      key={approval.id}
                      className="surface-instrument rounded-2xl border px-4 py-4"
                    >
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="space-y-2">
                          <p className="text-sm font-medium">
                            {summary.length > 180 ? `${summary.slice(0, 180)}...` : summary}
                          </p>
                          <div className="flex flex-wrap items-center gap-2">
                            {approval.task_agent_id ? (
                              <Badge variant="outline" className="text-xs">
                                {approval.task_agent_id}
                              </Badge>
                            ) : null}
                            {approval.task_priority ? (
                              <Badge variant="secondary" className="text-xs">
                                {approval.task_priority}
                              </Badge>
                            ) : null}
                            <Badge variant="outline" className="text-xs">
                              {approval.privilege_class}
                            </Badge>
                            <Badge variant="secondary" className="text-xs">
                              {approval.requested_action}
                            </Badge>
                            {approval.related_run_id ? (
                              <span className="text-xs text-muted-foreground">{approval.related_run_id}</span>
                            ) : null}
                            {approval.requested_at ? (
                              <span className="text-xs text-muted-foreground" data-volatile="true">
                                {formatRelativeTime(new Date(approval.requested_at * 1000).toISOString())}
                              </span>
                            ) : null}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            onClick={() => void approveMutation.mutateAsync(approval.id)}
                            disabled={approveMutation.isPending || !approval.id}
                          >
                            <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              void rejectMutation.mutateAsync({
                                approvalId: approval.id,
                                reason: "Rejected from operator console",
                              })
                            }
                            disabled={rejectMutation.isPending || !approval.id}
                          >
                            <XCircle className="mr-1.5 h-3.5 w-3.5" />
                            Reject
                          </Button>
                        </div>
                      </div>
                    </article>
                  );
                })
              ) : (
                <EmptyState
                  title="Queue clear"
                  description="No approval requests are waiting for operator action."
                  className="py-6"
                />
              )}
            </div>
          </div>

          <div className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
            <p className="page-eyebrow">Project-output review</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Pending governed artifacts</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              Hybrid project outputs stay visible here so repo-safe work does not stall while a governed review is waiting on the operator.
            </p>

            <div className="mt-5 space-y-3">
              {latestPendingProjectCandidate ? (
                <article className="surface-instrument rounded-2xl border px-4 py-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-foreground">{latestPendingProjectCandidate.title}</p>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline">{projectFactoryTopProjectLabel}</Badge>
                        {latestPendingProjectCandidate.acceptanceBacklogId ? (
                          <Badge variant="secondary">{latestPendingProjectCandidate.acceptanceBacklogId}</Badge>
                        ) : null}
                        {latestPendingProjectCandidate.acceptanceMode ? (
                          <Badge variant="outline">{latestPendingProjectCandidate.acceptanceMode}</Badge>
                        ) : null}
                        {latestPendingProjectCandidate.verificationStatus ? (
                          <Badge variant="outline">
                            {latestPendingProjectCandidate.verificationStatus.replaceAll("_", " ")}
                          </Badge>
                        ) : null}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {latestPendingProjectCandidate.nextAction ??
                          "Open the project-factory route and review the governed acceptance artifacts."}
                      </p>
                      {latestPendingProjectCandidate.deliverableRefs.length > 0 ? (
                        <div className="space-y-1 text-xs text-muted-foreground">
                          {latestPendingProjectCandidate.deliverableRefs.slice(0, 3).map((ref) => (
                            <p key={ref} className="truncate font-mono">
                              {ref}
                            </p>
                          ))}
                        </div>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2">
                      <Button asChild size="sm" variant="outline">
                        <Link href="/projects">Open Project Factory</Link>
                      </Button>
                    </div>
                  </div>
                </article>
              ) : (
                <EmptyState
                  title="No pending project-output review"
                  description={
                    projectFactoryStatus?.detail ??
                    "No governed project-output candidate is currently waiting on hybrid review."
                  }
                  className="py-6"
                />
              )}
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <div className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
            <p className="page-eyebrow">Governance posture</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Current guardrails</h2>
            <div className="mt-4 space-y-3">
              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <p className="page-eyebrow text-[10px]">Builder front door</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Badge
                    variant={
                      builderFrontDoor?.degraded || builderSharedPressure?.current_session_status === "result_attention"
                        ? "destructive"
                        : builderSharedPressure?.current_session_status === "review_required" ||
                            builderSharedPressure?.current_session_status === "needs_sync"
                          ? "outline"
                          : "secondary"
                    }
                  >
                    {builderPressureLabel}
                  </Badge>
                  {builderCurrent ? <Badge variant="outline">{builderCurrent.primary_adapter}</Badge> : null}
                  {builderCurrent?.resumable_handle ? <Badge variant="outline">resumable</Badge> : null}
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  {builderFrontDoor?.degraded
                    ? builderFrontDoor.detail ?? "Builder front door is degraded from this dashboard runtime."
                    : builderCurrent
                      ? builderNeedsSync
                        ? `${builderCurrent.current_route} is still reporting ${builderCurrent.status.replaceAll("_", " ")}, but the shared execution kernel has no matching review or result packet for this session yet.`
                        : `${builderCurrent.current_route} is live with ${builderSharedReviewCount} shared review hold(s), ${builderSharedResultCount} shared result alert(s), and ${builderCurrent.artifact_count} artifact(s).`
                      : "Open the builder desk to start a routed implementation lane."}
                </p>
                <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                  <p>Verification: {builderCurrent?.verification_status.replaceAll("_", " ") ?? "not started"}</p>
                  <p>Fallback: {builderCurrent?.fallback_state?.replaceAll("_", " ") ?? "none"}</p>
                  <p>Resumable: {builderCurrent?.resumable_handle ?? "not attached"}</p>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button asChild size="sm" variant="outline">
                    <Link href={builderCurrent ? `/builder?session=${builderCurrent.id}` : "/builder"}>Open Builder</Link>
                  </Button>
                </div>
              </div>

              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <p className="page-eyebrow text-[10px]">Steady-state front door</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {steadyState?.closureState ? <Badge variant="outline">{steadyState.closureState}</Badge> : null}
                  {steadyState?.operatorMode ? <Badge variant="outline">{steadyState.operatorMode}</Badge> : null}
                  {steadyState?.currentWork?.providerLabel ? <Badge variant="outline">{steadyState.currentWork.providerLabel}</Badge> : null}
                  {steadyState?.nextUp?.laneFamily ? <Badge variant="outline">{steadyState.nextUp.laneFamily}</Badge> : null}
                  <Badge variant="outline">{steadyStateSummary.sourceLabel}</Badge>
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  {steadyState
                    ? `${operatorAttentionLabel}. ${operatorAttentionSummary}`
                    : "The steady-state front door is not currently attached to the operator summary route."}
                </p>
                <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                  <p>Current work: {operatorCurrentWork}</p>
                  <p>Next up: {operatorNextUp}</p>
                  <p>{operatorNextUpDetail}</p>
                </div>
              </div>

              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <p className="page-eyebrow text-[10px]">Value throughput</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Badge variant={staleClaimCount > 0 || reconciliationIssueCount > 0 ? "outline" : "secondary"}>
                    {valueThroughputAvailable ? `${resultBackedCompletions} result-backed` : "feed offline"}
                  </Badge>
                  {valueThroughputAvailable ? (
                    <Badge variant="outline">{`${reviewBackedOutputs} review-backed`}</Badge>
                  ) : null}
                  {valueThroughputAvailable ? (
                    <Badge variant="outline">{`${staleClaimCount} stale claim${staleClaimCount === 1 ? "" : "s"}`}</Badge>
                  ) : null}
                  {valueThroughputAvailable && valueThroughputDegraded ? (
                    <Badge variant="outline">degraded feed</Badge>
                  ) : null}
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  {valueThroughputAvailable
                    ? valueThroughputDegraded && valueThroughputStatus?.detail
                      ? `${reviewDebtCount} review debt item${reviewDebtCount === 1 ? "" : "s"} remain, oldest age ${reviewDebtAge}h. Direct-control loops stay separate at ${directControlLoops}, and proposal-only loops are ${proposalOnlyLoops}. ${valueThroughputStatus.detail}`
                      : `${reviewDebtCount} review debt item${reviewDebtCount === 1 ? "" : "s"} remain, oldest age ${reviewDebtAge}h. Direct-control loops stay separate at ${directControlLoops}, and proposal-only loops are ${proposalOnlyLoops}.`
                    : valueThroughputStatus?.detail ?? "Value-throughput scorecard is not currently attached to the operator summary route."}
                </p>
              </div>

              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <p className="page-eyebrow text-[10px]">Autonomous value proof</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Badge variant={operatorValueStageMet ? "secondary" : "outline"}>
                    {autonomousValueAvailable ? `${acceptedOperatorValueCount} operator-value` : "feed offline"}
                  </Badge>
                  {autonomousValueAvailable ? (
                    <Badge variant={productValueStageMet ? "secondary" : "outline"}>
                      {`${acceptedProductValueCount} product-value`}
                    </Badge>
                  ) : null}
                  {autonomousValueAvailable ? (
                    <Badge variant={disqualifiedValueCount > 0 ? "outline" : "secondary"}>
                      {`${disqualifiedValueCount} disqualified`}
                    </Badge>
                  ) : null}
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  {autonomousValueAvailable
                    ? `Latest accepted proof: ${latestAcceptedTitle} on ${latestAcceptedSurface} via ${latestAcceptedKind}. Remaining ladder: ${remainingOperatorValue} operator-value and ${remainingProductValue} product-value proof${remainingOperatorValue + remainingProductValue === 1 ? "" : "s"}.`
                    : autonomousValueProofStatus?.detail ?? "Autonomous value proof is not currently attached to the operator summary route."}
                </p>
              </div>

              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={governance.launch_ready ? "secondary" : "outline"}>
                    {governanceAvailable ? currentMode : "feed offline"}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {governanceAvailable && governance.current_mode?.entered_at
                      ? formatRelativeTime(new Date(governance.current_mode.entered_at * 1000).toISOString())
                      : governanceAvailable
                        ? "Mode history unavailable"
                        : "Governance feed unavailable"}
                  </span>
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  {!governanceAvailable
                    ? "Operator governance posture is temporarily unavailable from this dashboard runtime."
                    : governance.attention_posture?.recommended_mode
                    ? `Recommended mode: ${governance.attention_posture.recommended_mode}.`
                    : "No alternate mode recommendation is active right now."}
                </p>
              </div>

              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <p className="page-eyebrow text-[10px]">Launch blockers</p>
                <div className="mt-3 space-y-2">
                  {launchBlockers.length > 0 ? (
                    launchBlockers.slice(0, 4).map((blocker) => (
                      <p key={blocker} className="text-sm text-[color:var(--signal-warning)]">
                        {blocker}
                      </p>
                    ))
                  ) : (
                    <p className="text-sm text-[color:var(--signal-success)]">Launch posture is clear.</p>
                  )}
                </div>
              </div>

              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <p className="page-eyebrow text-[10px]">Attention pressure</p>
                <div className="mt-3 space-y-2">
                  {attentionBreaches.length > 0 ? (
                    attentionBreaches.map((breach) => (
                      <p key={breach} className="text-sm text-muted-foreground">
                        {breach}
                      </p>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No active attention breaches are recorded.</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
            <p className="page-eyebrow">Route ownership</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">
              Keep this page as a command desk
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Operator is for decisions, guardrails, and direct intervention. The wider dispatch,
              queue, and capacity story belongs to the routes that own it.
            </p>

            <div className="mt-4 space-y-3">
              {masterAtlasDegraded ? (
                <div className="surface-instrument rounded-2xl border border-[color:var(--signal-warning)]/40 px-4 py-4">
                  <p className="page-eyebrow text-[10px] text-[color:var(--signal-warning)]">Dispatch map degraded</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {masterAtlasDetail}
                  </p>
                </div>
              ) : null}

              {!masterAtlasDegraded ? (
                <div className="surface-instrument rounded-2xl border px-4 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="page-eyebrow text-[10px]">Governed dispatch handoff</p>
                    <Badge variant={governedDispatchHealthy ? "secondary" : "outline"}>
                      {governedDispatch?.task_status ?? governedDispatch?.status ?? "pending publication"}
                    </Badge>
                    {governedDispatch?.governor_level ? (
                      <Badge variant="outline">Level {governedDispatch.governor_level}</Badge>
                    ) : null}
                    {masterAtlas?.turnover_readiness?.work_economy_status ? (
                      <Badge variant="outline">{masterAtlas.turnover_readiness.work_economy_status}</Badge>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {governedDispatch?.current_task_title
                      ? `${governedDispatch.current_task_title} is the current governed handoff. The backlog is ${governedDispatch.backlog_status ?? "unpublished"}, task state is ${governedDispatch.task_status ?? "unknown"}, and the dispatch lane is ${governedDispatch.dispatch_outcome ?? "awaiting publication"}.`
                      : "The master atlas is available, but no governed dispatch handoff is published right now."}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    {masterAtlas?.turnover_readiness?.dispatchable_autonomous_queue_count != null ? (
                      <span className="rounded-full border border-border/70 px-2.5 py-1">
                        {masterAtlas.turnover_readiness.dispatchable_autonomous_queue_count} dispatchable
                      </span>
                    ) : null}
                    {masterAtlas?.turnover_readiness?.top_dispatchable_autonomous_task_title ? (
                      <span className="rounded-full border border-border/70 px-2.5 py-1">
                        next {masterAtlas.turnover_readiness.top_dispatchable_autonomous_task_title}
                      </span>
                    ) : null}
                    {masterAtlas?.governed_dispatch_execution_report_path ? (
                      <span className="rounded-full border border-border/70 px-2.5 py-1">
                        atlas backed
                      </span>
                    ) : null}
                  </div>
                </div>
              ) : null}

              <div className="surface-instrument rounded-2xl border px-4 py-4">
                <p className="page-eyebrow text-[10px]">Use the owning surfaces</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Routing owns lane policy, dispatch, and work-economy posture. Topology owns node capacity,
                  the master atlas, and the live system map. Governor owns cross-surface control-plane posture.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link
                    href="/routing"
                    className="surface-metric rounded-full border px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-accent/40 hover:text-foreground"
                  >
                    Open Routing
                  </Link>
                  <Link
                    href="/topology"
                    className="surface-metric rounded-full border px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-accent/40 hover:text-foreground"
                  >
                    Open Topology
                  </Link>
                  <Link
                    href="/governor"
                    className="surface-metric rounded-full border px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-accent/40 hover:text-foreground"
                  >
                    Open Governor
                  </Link>
                </div>
              </div>

            </div>
          </div>

          <div className="surface-panel flex min-h-[28rem] flex-col overflow-hidden rounded-[28px] border">
            <div className="border-b border-border/70 px-5 py-4 sm:px-6">
              <p className="page-eyebrow">Meta-Orchestrator</p>
              <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Direct command lane</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                Chat stays here as a high-power tool, but not as the primary organizing surface for the route.
              </p>
            </div>

            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <ScrollArea className="flex-1 px-4 sm:px-6" ref={scrollRef}>
                <div className="space-y-4 py-4">
                  {messages.length === 0 ? (
                    <EmptyState
                      title="Ready for commands"
                      description="Ask the meta-orchestrator about system state, plans, or overnight activity."
                      className="py-6"
                    />
                  ) : (
                    messages.map((msg) => (
                      <div key={msg.id}>
                        {msg.role === "user" ? (
                          <div className="flex justify-end">
                            <div className="max-w-[88%] rounded-2xl bg-primary px-4 py-3 text-primary-foreground sm:max-w-[78%]">
                              <div className="mb-2 flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.2em] opacity-70">
                                <span>Operator</span>
                                <span data-volatile="true">{formatRelativeTime(msg.createdAt)}</span>
                              </div>
                              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                            </div>
                          </div>
                        ) : (
                          <div className="flex max-w-[92%] flex-col gap-2 sm:max-w-[84%]">
                            <div className="rounded-2xl bg-muted px-4 py-3 text-foreground">
                              <div className="mb-2 flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                                <span>Orchestrator</span>
                                <span data-volatile="true">{formatRelativeTime(msg.createdAt)}</span>
                              </div>
                              {msg.content ? (
                                <RichText content={msg.content} />
                              ) : isStreaming ? (
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                  <LoaderCircle className="h-4 w-4 animate-spin" />
                                  Streaming...
                                </div>
                              ) : null}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>

              {error ? (
                <div className="mx-4 mb-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive sm:mx-6">
                  {error}
                </div>
              ) : null}

              <div className="border-t border-border/70 px-4 py-3 sm:px-6">
                <div className="mb-3 flex flex-wrap gap-2">
                  {SUGGESTED_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      className="surface-metric rounded-full border px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-accent/40 hover:text-foreground"
                      onClick={() => void sendMessage(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>

                <form
                  className="flex flex-col gap-2 sm:flex-row"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void sendMessage();
                  }}
                >
                  <Input
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                        event.preventDefault();
                        void sendMessage();
                      }
                    }}
                    placeholder="Message the meta-orchestrator..."
                    disabled={isStreaming}
                    className="flex-1"
                    autoFocus
                  />
                  {isStreaming ? (
                    <Button type="button" variant="outline" onClick={() => abortRef.current?.abort()}>
                      <Square className="mr-2 h-4 w-4" />
                      Stop
                    </Button>
                  ) : null}
                  <Button type="submit" disabled={!input.trim() || isStreaming}>
                    <Send className="mr-2 h-4 w-4" />
                    Send
                  </Button>
                </form>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
