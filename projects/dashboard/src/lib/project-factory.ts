import { access, readFile } from "node:fs/promises";
import { candidateTruthInventoryPaths, type TruthInventoryCandidatePath, type TruthInventorySourceKind } from "@/lib/truth-inventory-paths";

export type ProjectFactorySourceKind = TruthInventorySourceKind;
type ArtifactCandidatePath = TruthInventoryCandidatePath<ProjectFactorySourceKind>;

interface ArtifactReadResult {
  raw: Record<string, any> | null;
  kind: ProjectFactorySourceKind | null;
  path: string | null;
  error: string | null;
}

export interface ProjectFactoryCandidateRecord {
  candidateId: string;
  projectId: string;
  title: string;
  deliverableKind: string;
  deliverableRefs: string[];
  verificationRefs: string[];
  workflowRefs: string[];
  manifestRef: string | null;
  acceptanceBacklogId: string | null;
  acceptanceMode: string | null;
  acceptanceState: string | null;
  approvalPosture: string | null;
  verificationStatus: string | null;
  nextAction: string | null;
  generatedAt: string | null;
  sourceGenerator: string | null;
}

export interface ProjectFactoryAcceptedEntry {
  projectId: string;
  title: string;
  deliverableKind: string;
  deliverableRefs: string[];
  acceptedAt: string | null;
  acceptedBy: string | null;
  beneficiarySurface: string | null;
  valueClass: string | null;
}

export interface ProjectFactoryProjectRecord {
  projectId: string;
  label: string;
  canonicalRoot: string;
  projectClass: string;
  platformClass: string;
  authorityClass: string;
  authorityCleanliness: string;
  autonomyEligibility: string;
  readinessTier: string;
  buildHealth: string;
  safeSurfaceStatus: string;
  safeSurfaceExpectation: string;
  routingClass: string;
  factoryPriority: number;
  firstOutputTarget: string;
  nextTranche: string;
  blockers: string[];
  verificationBundle: string[];
  acceptanceBundle: string[];
  isFirstClass: boolean;
  isTopPriority: boolean;
  candidateCount: number;
  pendingCandidateCount: number;
  acceptedCandidateCount: number;
  latestCandidate: ProjectFactoryCandidateRecord | null;
  latestAcceptedEntry: ProjectFactoryAcceptedEntry | null;
}

export interface CommandCenterFinalFormGap {
  id: string;
  route: string;
  severity: string;
  tranche: string;
  verificationState: string;
  detail: string;
  lastSuccessfulEvidencePassAt: string | null;
}

export interface CommandCenterFinalFormStatus {
  generatedAt: string;
  status: string;
  done: boolean;
  summary: {
    openGapCount: number;
    highestSeverity: string;
    consecutiveCleanUiAuditPassCount: number;
    latestUiAuditGeneratedAt: string | null;
    latestUiAuditClean: boolean;
    latestUiAuditFailureCount: number;
  };
  openGaps: CommandCenterFinalFormGap[];
}

export interface ProjectFactoryConsoleSnapshot {
  generatedAt: string;
  available: boolean;
  degraded: boolean;
  detail: string | null;
  firstClassProjectIds: string[];
  summary: {
    operatingMode: string;
    topPriorityProjectId: string | null;
    topPriorityProjectLabel: string | null;
    acceptedProjectOutputCount: number;
    pendingCandidateCount: number;
    pendingHybridAcceptanceCount: number;
    latestPendingProjectId: string | null;
    broadProjectFactoryReady: boolean;
    projectOutputStageMet: boolean;
    distinctProjectCount: number;
    eligibleNowCount: number;
  };
  coreRuntimeGate: {
    proofGateOpen: boolean;
    continuityHealthStatus: string;
    runtimeParityClass: string;
    singleLiveBlocker: string;
    stableOperatingDayMet: boolean;
    stableOperatingDayHours: number;
    stableOperatingDayRequiredHours: number;
    blockingCheckIds: string[];
  };
  latestPendingCandidate: ProjectFactoryCandidateRecord | null;
  latestAcceptedEntry: ProjectFactoryAcceptedEntry | null;
  acceptedEntries: ProjectFactoryAcceptedEntry[];
  pendingCandidates: ProjectFactoryCandidateRecord[];
  firstClassProjects: ProjectFactoryProjectRecord[];
  baselineProjects: ProjectFactoryProjectRecord[];
  projects: ProjectFactoryProjectRecord[];
  finalFormStatus: CommandCenterFinalFormStatus | null;
  sourcePaths: Record<string, string | null>;
}

const FIRST_CLASS_PROJECT_IDS = ["eoq", "lawnsignal", "ulrich-website", "field-inspect"];

function reportArtifactCandidates(fileName: string): ArtifactCandidatePath[] {
  return candidateTruthInventoryPaths(fileName);
}

function toNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function toStringList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item: unknown): item is string => typeof item === "string" && item.length > 0)
    : [];
}

async function readArtifact(fileName: string): Promise<ArtifactReadResult> {
  for (const candidate of reportArtifactCandidates(fileName)) {
    try {
      await access(candidate.path);
    } catch {
      continue;
    }

    try {
      const raw = JSON.parse(await readFile(candidate.path, "utf-8")) as Record<string, any>;
      return {
        raw,
        kind: candidate.kind,
        path: candidate.path,
        error: null,
      };
    } catch (error) {
      return {
        raw: null,
        kind: candidate.kind,
        path: candidate.path,
        error: `Invalid JSON at ${candidate.path}: ${error instanceof Error ? error.message : "unknown parse error"}`,
      };
    }
  }

  return {
    raw: null,
    kind: null,
    path: null,
    error: `Missing truth artifact: ${fileName}`,
  };
}

function buildCandidateRecord(raw: Record<string, any>): ProjectFactoryCandidateRecord {
  return {
    candidateId: toString(raw.candidate_id, "unknown"),
    projectId: toString(raw.project_id || raw.source_project_id, "unknown"),
    title: toString(raw.title, "Untitled candidate"),
    deliverableKind: toString(raw.deliverable_kind, "unknown"),
    deliverableRefs: toStringList(raw.deliverable_refs),
    verificationRefs: toStringList(raw.verification_refs),
    workflowRefs: toStringList(raw.workflow_refs),
    manifestRef: typeof raw.manifest_ref === "string" ? raw.manifest_ref : null,
    acceptanceBacklogId: typeof raw.acceptance_backlog_id === "string" ? raw.acceptance_backlog_id : null,
    acceptanceMode: typeof raw.acceptance_mode === "string" ? raw.acceptance_mode : null,
    acceptanceState: typeof raw.acceptance_state === "string" ? raw.acceptance_state : null,
    approvalPosture: typeof raw.approval_posture === "string" ? raw.approval_posture : null,
    verificationStatus: typeof raw.verification_status === "string" ? raw.verification_status : null,
    nextAction: typeof raw.next_action === "string" ? raw.next_action : null,
    generatedAt: typeof raw.generated_at === "string" ? raw.generated_at : null,
    sourceGenerator: typeof raw.source_generator === "string" ? raw.source_generator : null,
  };
}

function buildAcceptedEntry(raw: Record<string, any>): ProjectFactoryAcceptedEntry {
  return {
    projectId: toString(raw.project_id || raw.source_project_id, "unknown"),
    title: toString(raw.title, "Accepted output"),
    deliverableKind: toString(raw.deliverable_kind, "unknown"),
    deliverableRefs: toStringList(raw.deliverable_refs),
    acceptedAt: typeof raw.accepted_at === "string" ? raw.accepted_at : null,
    acceptedBy: typeof raw.accepted_by === "string" ? raw.accepted_by : null,
    beneficiarySurface: typeof raw.beneficiary_surface === "string" ? raw.beneficiary_surface : null,
    valueClass: typeof raw.value_class === "string" ? raw.value_class : null,
  };
}

function byLatestAccepted(left: ProjectFactoryAcceptedEntry, right: ProjectFactoryAcceptedEntry) {
  return (right.acceptedAt ?? "").localeCompare(left.acceptedAt ?? "");
}

function byLatestGenerated(left: ProjectFactoryCandidateRecord, right: ProjectFactoryCandidateRecord) {
  return (right.generatedAt ?? "").localeCompare(left.generatedAt ?? "");
}

export async function loadProjectFactorySnapshot(): Promise<ProjectFactoryConsoleSnapshot> {
  const [readinessRead, proofRead, candidatesRead, finalFormRead] = await Promise.all([
    readArtifact("project-output-readiness.json"),
    readArtifact("project-output-proof.json"),
    readArtifact("project-output-candidates.json"),
    readArtifact("command-center-final-form-status.json"),
  ]);

  const sourcePaths = {
    readiness: readinessRead.path,
    proof: proofRead.path,
    candidates: candidatesRead.path,
    finalFormStatus: finalFormRead.path,
  };

  const detailErrors = [readinessRead.error, proofRead.error, candidatesRead.error, finalFormRead.error].filter(
    (value): value is string => typeof value === "string" && value.length > 0,
  );

  const readiness = readinessRead.raw ?? {};
  const proof = proofRead.raw ?? {};
  const candidates = candidatesRead.raw ?? {};
  const finalFormRaw = finalFormRead.raw ?? {};

  const candidateRecords = (Array.isArray(candidates.candidates) ? candidates.candidates : [])
    .filter((item: unknown): item is Record<string, any> => Boolean(item && typeof item === "object"))
    .map(buildCandidateRecord)
    .sort(byLatestGenerated);
  const acceptedEntries = (Array.isArray(proof.accepted_entries) ? proof.accepted_entries : [])
    .filter((item: unknown): item is Record<string, any> => Boolean(item && typeof item === "object"))
    .map(buildAcceptedEntry)
    .sort(byLatestAccepted);

  const projects = (Array.isArray(readiness.projects) ? readiness.projects : [])
    .filter((item: unknown): item is Record<string, any> => Boolean(item && typeof item === "object"))
    .map((project) => {
      const projectId = toString(project.project_id, "unknown");
      const latestCandidate =
        candidateRecords.find((candidate) => candidate.projectId === projectId) ?? null;
      const latestAcceptedEntry =
        acceptedEntries.find((candidate) => candidate.projectId === projectId) ?? null;
      const projectSummary =
        candidates.project_summaries && typeof candidates.project_summaries === "object"
          ? (candidates.project_summaries[projectId] as Record<string, any> | undefined)
          : undefined;

      return {
        projectId,
        label: toString(project.label, projectId),
        canonicalRoot: toString(project.canonical_root, "unknown"),
        projectClass: toString(project.project_class, "unknown"),
        platformClass: toString(project.platform_class, "unknown"),
        authorityClass: toString(project.authority_class, "unknown"),
        authorityCleanliness: toString(project.authority_cleanliness, "unknown"),
        autonomyEligibility: toString(project.autonomy_eligibility, "unknown"),
        readinessTier: toString(project.readiness_tier, "unknown"),
        buildHealth: toString(project.build_health, "unknown"),
        safeSurfaceStatus: toString(project.safe_surface_status, "unknown"),
        safeSurfaceExpectation: toString(project.safe_surface_expectation, "unknown"),
        routingClass: toString(project.routing_class, "unknown"),
        factoryPriority: toNumber(project.factory_priority),
        firstOutputTarget: toString(project.first_output_target, "No target recorded."),
        nextTranche: toString(project.next_tranche, "No next tranche recorded."),
        blockers: toStringList(project.blockers),
        verificationBundle: toStringList(project.verification_bundle),
        acceptanceBundle: toStringList(project.acceptance_bundle),
        isFirstClass: FIRST_CLASS_PROJECT_IDS.includes(projectId),
        isTopPriority: projectId === toString(readiness.top_priority_project_id),
        candidateCount: toNumber(projectSummary?.candidate_count),
        pendingCandidateCount: toNumber(projectSummary?.pending_candidate_count),
        acceptedCandidateCount: toNumber(projectSummary?.accepted_candidate_count),
        latestCandidate,
        latestAcceptedEntry,
      } satisfies ProjectFactoryProjectRecord;
    })
    .sort((left, right) => {
      if (left.factoryPriority !== right.factoryPriority) {
        return left.factoryPriority - right.factoryPriority;
      }
      return left.label.localeCompare(right.label);
    });

  const firstClassProjects = projects.filter((project) => project.isFirstClass);
  const baselineProjects = projects.filter((project) => !project.isFirstClass);
  const latestPendingCandidate =
    finalFormRead.raw && finalFormRaw.summary
      ? candidateRecords.find(
          (candidate) => candidate.projectId === toString(finalFormRaw.summary?.latest_pending_project_id),
        ) ?? (candidateRecords.find((candidate) => candidate.acceptanceState === "pending_acceptance") ?? null)
      : candidateRecords.find((candidate) => candidate.acceptanceState === "pending_acceptance") ?? null;

  const finalFormStatus =
    finalFormRead.raw && typeof finalFormRead.raw === "object"
      ? {
          generatedAt: toString(finalFormRaw.generated_at),
          status: toString(finalFormRaw.status, "unknown"),
          done: Boolean(finalFormRaw.done),
          summary: {
            openGapCount: toNumber(finalFormRaw.summary?.open_gap_count),
            highestSeverity: toString(finalFormRaw.summary?.highest_severity, "none"),
            consecutiveCleanUiAuditPassCount: toNumber(finalFormRaw.summary?.consecutive_clean_ui_audit_pass_count),
            latestUiAuditGeneratedAt:
              typeof finalFormRaw.summary?.latest_ui_audit_generated_at === "string"
                ? finalFormRaw.summary.latest_ui_audit_generated_at
                : null,
            latestUiAuditClean: Boolean(finalFormRaw.summary?.latest_ui_audit_clean),
            latestUiAuditFailureCount: toNumber(finalFormRaw.summary?.latest_ui_audit_failure_count),
          },
          openGaps: (Array.isArray(finalFormRaw.open_gaps) ? finalFormRaw.open_gaps : [])
            .filter((item: unknown): item is Record<string, any> => Boolean(item && typeof item === "object"))
            .map((gap) => ({
              id: toString(gap.id, "unknown"),
              route: toString(gap.route, "/"),
              severity: toString(gap.severity, "unknown"),
              tranche: toString(gap.tranche, "unknown"),
              verificationState: toString(gap.verification_state, "unknown"),
              detail: toString(gap.detail, "No detail recorded."),
              lastSuccessfulEvidencePassAt:
                typeof gap.last_successful_evidence_pass_at === "string"
                  ? gap.last_successful_evidence_pass_at
                  : null,
            })),
        }
      : null;

  return {
    generatedAt:
      toString(finalFormRaw.generated_at) ||
      toString(candidates.generated_at) ||
      toString(proof.generated_at) ||
      toString(readiness.generated_at),
    available: Boolean(readinessRead.raw && proofRead.raw && candidatesRead.raw),
    degraded: detailErrors.length > 0,
    detail: detailErrors.length > 0 ? detailErrors.join(" · ") : null,
    firstClassProjectIds: [...FIRST_CLASS_PROJECT_IDS],
    summary: {
      operatingMode: toString(readiness.factory_operating_mode, "unknown"),
      topPriorityProjectId:
        typeof readiness.top_priority_project_id === "string" ? readiness.top_priority_project_id : null,
      topPriorityProjectLabel:
        typeof readiness.top_priority_project_label === "string" ? readiness.top_priority_project_label : null,
      acceptedProjectOutputCount: toNumber(proof.accepted_project_output_count),
      pendingCandidateCount: toNumber(proof.pending_candidate_count),
      pendingHybridAcceptanceCount: toNumber(proof.pending_hybrid_acceptance_count),
      latestPendingProjectId:
        typeof proof.latest_pending_candidate?.project_id === "string"
          ? proof.latest_pending_candidate.project_id
          : null,
      broadProjectFactoryReady: Boolean(readiness.summary?.broad_project_factory_ready),
      projectOutputStageMet: Boolean(proof.stage_status?.met),
      distinctProjectCount: toNumber(proof.distinct_project_count),
      eligibleNowCount: toNumber(readiness.summary?.eligible_now_count),
    },
    coreRuntimeGate: {
      proofGateOpen: Boolean(readiness.core_runtime_gate?.proof_gate_open),
      continuityHealthStatus: toString(readiness.core_runtime_gate?.continuity_health_status, "unknown"),
      runtimeParityClass: toString(readiness.core_runtime_gate?.runtime_parity_class, "unknown"),
      singleLiveBlocker: toString(readiness.core_runtime_gate?.single_live_blocker, "unknown"),
      stableOperatingDayMet: Boolean(readiness.core_runtime_gate?.stable_operating_day_met),
      stableOperatingDayHours: toNumber(readiness.core_runtime_gate?.stable_operating_day_hours),
      stableOperatingDayRequiredHours: toNumber(readiness.core_runtime_gate?.stable_operating_day_required_hours),
      blockingCheckIds: toStringList(readiness.core_runtime_gate?.blocking_check_ids),
    },
    latestPendingCandidate,
    latestAcceptedEntry:
      typeof proof.latest_accepted_entry === "object" && proof.latest_accepted_entry
        ? buildAcceptedEntry(proof.latest_accepted_entry)
        : null,
    acceptedEntries,
    pendingCandidates: candidateRecords.filter((candidate) => candidate.acceptanceState !== "accepted"),
    firstClassProjects,
    baselineProjects,
    projects,
    finalFormStatus,
    sourcePaths,
  };
}
