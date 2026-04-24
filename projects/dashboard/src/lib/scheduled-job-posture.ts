import type { ScheduledJobRecord } from "@/lib/contracts";

export type ScheduledExecutionMode = "materialized_to_backlog" | "executed_directly";
export type ScheduledExecutionPlane = "queue" | "direct_control" | "proposal_only";
export type ScheduledJobPressureSummary = {
  totalJobs: number;
  queueBackedJobs: number;
  directJobs: number;
  proposalOnlyJobs: number;
  blockedJobs: number;
  needsSyncJobs: number;
};

const BLOCKED_ADMISSION_CLASSIFICATIONS = new Set([
  "blocked_by_headroom",
  "blocked_by_queue_priority",
  "blocked_by_review_debt",
]);

function normalize(value: string | null | undefined) {
  return String(value ?? "").trim();
}

export function classifyScheduledJobExecutionMode(
  job: Pick<ScheduledJobRecord, "id" | "last_execution_mode">,
): ScheduledExecutionMode {
  const explicit = normalize(job.last_execution_mode);
  if (explicit === "materialized_to_backlog" || explicit === "executed_directly") {
    return explicit;
  }

  const id = normalize(job.id);
  if (id === "agent-schedule:coding-agent" || id.startsWith("research:")) {
    return "materialized_to_backlog";
  }

  return "executed_directly";
}

export function classifyScheduledJobExecutionPlane(
  job: Pick<ScheduledJobRecord, "id" | "last_execution_mode" | "last_execution_plane">,
): ScheduledExecutionPlane {
  const explicit = normalize(job.last_execution_plane);
  if (explicit === "queue" || explicit === "direct_control" || explicit === "proposal_only") {
    return explicit;
  }

  if (classifyScheduledJobExecutionMode(job) === "materialized_to_backlog") {
    return "queue";
  }

  const id = normalize(job.id);
  if (id === "benchmark-cycle" || id === "improvement-cycle" || id === "nightly-optimization") {
    return "proposal_only";
  }

  return "direct_control";
}

export function classifyScheduledJobAdmission(
  job: Pick<ScheduledJobRecord, "id" | "last_execution_mode" | "last_execution_plane" | "last_admission_classification">,
) {
  const explicit = normalize(job.last_admission_classification);
  if (explicit.length > 0) {
    return explicit;
  }
  return classifyScheduledJobExecutionPlane(job);
}

export function isScheduledJobQueueBacked(
  job: Pick<ScheduledJobRecord, "id" | "last_execution_mode" | "last_execution_plane">,
): boolean {
  return classifyScheduledJobExecutionPlane(job) === "queue";
}

export function isScheduledJobProposalOnly(
  job: Pick<ScheduledJobRecord, "id" | "last_execution_mode" | "last_execution_plane">,
): boolean {
  return classifyScheduledJobExecutionPlane(job) === "proposal_only";
}

export function isScheduledJobBlocked(
  job: Pick<ScheduledJobRecord, "id" | "last_execution_mode" | "last_execution_plane" | "last_admission_classification">,
): boolean {
  return BLOCKED_ADMISSION_CLASSIFICATIONS.has(classifyScheduledJobAdmission(job));
}

export function scheduledJobNeedsSync(
  job: Pick<ScheduledJobRecord, "id" | "last_execution_mode" | "last_execution_plane" | "last_backlog_id">,
): boolean {
  return (
    classifyScheduledJobExecutionPlane(job) === "queue"
    && normalize(job.last_execution_mode) === "materialized_to_backlog"
    && normalize(job.last_backlog_id).length === 0
  );
}

export function summarizeScheduledJobPressure(
  jobs: Array<
    Pick<
      ScheduledJobRecord,
      "id" | "last_execution_mode" | "last_execution_plane" | "last_admission_classification" | "last_backlog_id"
    >
  >,
): ScheduledJobPressureSummary {
  return jobs.reduce<ScheduledJobPressureSummary>(
    (summary, job) => {
      summary.totalJobs += 1;
      if (classifyScheduledJobExecutionPlane(job) === "queue") {
        summary.queueBackedJobs += 1;
      } else if (classifyScheduledJobExecutionPlane(job) === "proposal_only") {
        summary.proposalOnlyJobs += 1;
      } else {
        summary.directJobs += 1;
      }
      if (isScheduledJobBlocked(job)) {
        summary.blockedJobs += 1;
      }
      if (scheduledJobNeedsSync(job)) {
        summary.needsSyncJobs += 1;
      }
      return summary;
    },
    {
      totalJobs: 0,
      queueBackedJobs: 0,
      directJobs: 0,
      proposalOnlyJobs: 0,
      blockedJobs: 0,
      needsSyncJobs: 0,
    },
  );
}
