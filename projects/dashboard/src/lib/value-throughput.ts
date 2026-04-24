import { access, readFile } from "node:fs/promises";
import { candidateTruthInventoryPaths, type TruthInventoryCandidatePath, type TruthInventorySourceKind } from "@/lib/truth-inventory-paths";

export type ValueThroughputSourceKind = TruthInventorySourceKind;
type ValueThroughputCandidatePath = TruthInventoryCandidatePath<ValueThroughputSourceKind>;

export interface ValueThroughputScorecard {
  generatedAt: string;
  degradedSections: string[];
  resultBackedCompletionCount: number;
  reviewBackedOutputCount: number;
  staleClaimCount: number;
  backlogAging: {
    openItemCount: number;
    byFamily: Array<{
      family: string;
      count: number;
      oldestAgeHours: number;
      averageAgeHours: number;
    }>;
    byProject: Array<{
      projectId: string;
      count: number;
      oldestAgeHours: number;
      averageAgeHours: number;
    }>;
  };
  dispatchToResultLatency: {
    completedCount: number;
    averageHours: number;
  };
  proposalConversion: {
    proposalBacklogCount: number;
    resultBackedCompletionCount: number;
    reviewBackedOutputCount: number;
  };
  reviewDebt: {
    count: number;
    oldestAgeHours: number;
    byFamily: Array<{
      family: string;
      count: number;
      oldestAgeHours: number;
      averageAgeHours: number;
    }>;
  };
  scheduledExecution: {
    queueBackedJobs: number;
    directControlJobs: number;
    proposalOnlyJobs: number;
    blockedJobs: number;
    needsSyncJobs: number;
  };
  reconciliation: {
    issueCount: number;
    repairableCount: number;
    issuesByType: Record<string, number>;
    issues: Array<{
      backlogId: string;
      title: string;
      family: string;
      projectId: string;
      status: string;
      issueType: string;
      repairAction: string;
      detail: string;
    }>;
  };
  sourceKind: ValueThroughputSourceKind;
  sourcePath: string;
}

export interface ValueThroughputReadStatus {
  available: boolean;
  degraded: boolean;
  detail: string | null;
  sourceKind: ValueThroughputSourceKind | null;
  sourcePath: string | null;
}

export interface ValueThroughputReadResult {
  scorecard: ValueThroughputScorecard | null;
  status: ValueThroughputReadStatus;
}

function candidatePaths(): ValueThroughputCandidatePath[] {
  return candidateTruthInventoryPaths("value-throughput-scorecard.json");
}

function toNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function buildScorecard(raw: Record<string, any>, candidate: ValueThroughputCandidatePath): ValueThroughputScorecard {
  return {
    generatedAt: typeof raw.generated_at === "string" ? raw.generated_at : "",
    degradedSections: Array.isArray(raw.degraded_sections)
      ? raw.degraded_sections.filter((item: unknown): item is string => typeof item === "string" && item.length > 0)
      : [],
    resultBackedCompletionCount: toNumber(raw.result_backed_completion_count),
    reviewBackedOutputCount: toNumber(raw.review_backed_output_count),
    staleClaimCount: toNumber(raw.stale_claim_count),
    backlogAging: {
      openItemCount: toNumber(raw.backlog_aging?.open_item_count),
      byFamily: Array.isArray(raw.backlog_aging?.by_family)
        ? raw.backlog_aging.by_family.map((item: Record<string, unknown>) => ({
            family: typeof item.family === "string" ? item.family : "unknown",
            count: toNumber(item.count),
            oldestAgeHours: toNumber(item.oldest_age_hours),
            averageAgeHours: toNumber(item.average_age_hours),
          }))
        : [],
      byProject: Array.isArray(raw.backlog_aging?.by_project)
        ? raw.backlog_aging.by_project.map((item: Record<string, unknown>) => ({
            projectId: typeof item.project_id === "string" ? item.project_id : "unscoped",
            count: toNumber(item.count),
            oldestAgeHours: toNumber(item.oldest_age_hours),
            averageAgeHours: toNumber(item.average_age_hours),
          }))
        : [],
    },
    dispatchToResultLatency: {
      completedCount: toNumber(raw.dispatch_to_result_latency?.completed_count),
      averageHours: toNumber(raw.dispatch_to_result_latency?.average_hours),
    },
    proposalConversion: {
      proposalBacklogCount: toNumber(raw.proposal_conversion?.proposal_backlog_count),
      resultBackedCompletionCount: toNumber(raw.proposal_conversion?.result_backed_completion_count),
      reviewBackedOutputCount: toNumber(raw.proposal_conversion?.review_backed_output_count),
    },
    reviewDebt: {
      count: toNumber(raw.review_debt?.count),
      oldestAgeHours: toNumber(raw.review_debt?.oldest_age_hours),
      byFamily: Array.isArray(raw.review_debt?.by_family)
        ? raw.review_debt.by_family.map((item: Record<string, unknown>) => ({
            family: typeof item.family === "string" ? item.family : "unknown",
            count: toNumber(item.count),
            oldestAgeHours: toNumber(item.oldest_age_hours),
            averageAgeHours: toNumber(item.average_age_hours),
          }))
        : [],
    },
    scheduledExecution: {
      queueBackedJobs: toNumber(raw.scheduled_execution?.queue_backed_jobs),
      directControlJobs: toNumber(raw.scheduled_execution?.direct_control_jobs),
      proposalOnlyJobs: toNumber(raw.scheduled_execution?.proposal_only_jobs),
      blockedJobs: toNumber(raw.scheduled_execution?.blocked_jobs),
      needsSyncJobs: toNumber(raw.scheduled_execution?.needs_sync_jobs),
    },
    reconciliation: {
      issueCount: toNumber(raw.reconciliation?.issue_count),
      repairableCount: toNumber(raw.reconciliation?.repairable_count),
      issuesByType:
        raw.reconciliation?.issues_by_type && typeof raw.reconciliation.issues_by_type === "object"
          ? { ...(raw.reconciliation.issues_by_type as Record<string, number>) }
          : {},
      issues: Array.isArray(raw.reconciliation?.issues)
        ? raw.reconciliation.issues.map((item: Record<string, unknown>) => ({
            backlogId: typeof item.backlog_id === "string" ? item.backlog_id : "",
            title: typeof item.title === "string" ? item.title : "",
            family: typeof item.family === "string" ? item.family : "",
            projectId: typeof item.project_id === "string" ? item.project_id : "",
            status: typeof item.status === "string" ? item.status : "",
            issueType: typeof item.issue_type === "string" ? item.issue_type : "",
            repairAction: typeof item.repair_action === "string" ? item.repair_action : "",
            detail: typeof item.detail === "string" ? item.detail : "",
          }))
        : [],
    },
    sourceKind: candidate.kind,
    sourcePath: candidate.path,
  };
}

export async function loadValueThroughputScorecard(): Promise<ValueThroughputReadResult> {
  for (const candidate of candidatePaths()) {
    try {
      await access(candidate.path);
    } catch {
      continue;
    }

    try {
      const text = await readFile(candidate.path, "utf-8");
      const raw = JSON.parse(text) as Record<string, any>;
      const scorecard = buildScorecard(raw, candidate);
      const degradedDetail =
        scorecard.degradedSections.length > 0
          ? `Value-throughput scorecard is running in degraded mode: ${scorecard.degradedSections.join(" · ")}`
          : null;
      return {
        scorecard,
        status: {
          available: true,
          degraded: Boolean(degradedDetail),
          detail: degradedDetail,
          sourceKind: candidate.kind,
          sourcePath: candidate.path,
        },
      };
    } catch (error) {
      return {
        scorecard: null,
        status: {
          available: false,
          degraded: true,
          detail: `Invalid value-throughput scorecard at ${candidate.path}: ${error instanceof Error ? error.message : "unknown parse error"}`,
          sourceKind: candidate.kind,
          sourcePath: candidate.path,
        },
      };
    }
  }

  return {
    scorecard: null,
    status: {
      available: false,
      degraded: true,
      detail: "Value-throughput scorecard was not found in the workspace report or repo-root fallback path.",
      sourceKind: null,
      sourcePath: null,
    },
  };
}
