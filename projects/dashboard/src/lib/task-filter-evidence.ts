import type { WorkforceTask } from "@/lib/contracts";

export type SharedTaskFilter = "all" | "queued" | "approval" | "running" | "completed" | "failed";
export type SharedTaskPresentationState =
  | "queued"
  | "approval"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "needs_sync";
export type SharedTaskPresentationTone = "info" | "review" | "success" | "danger" | "warning";

type TaskEvidenceFields = Pick<WorkforceTask, "status" | "reviewId" | "resultId">;

const PRESENTATION_LABELS: Record<SharedTaskPresentationState, string> = {
  queued: "Queued",
  approval: "Needs approval",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
  needs_sync: "Needs sync",
};

const PRESENTATION_TONES: Record<SharedTaskPresentationState, SharedTaskPresentationTone> = {
  queued: "info",
  approval: "review",
  running: "info",
  completed: "success",
  failed: "danger",
  cancelled: "info",
  needs_sync: "warning",
};

export function hasApprovalReviewEvidence(task: Pick<WorkforceTask, "status" | "reviewId">) {
  return task.status === "pending_approval" && Boolean(task.reviewId);
}

export function hasFailedResultEvidence(task: Pick<WorkforceTask, "status" | "resultId">) {
  return task.status === "failed" && Boolean(task.resultId);
}

export function matchesSharedTaskFilter(task: TaskEvidenceFields, filter: SharedTaskFilter) {
  switch (filter) {
    case "approval":
      return hasApprovalReviewEvidence(task);
    case "running":
      return task.status === "running";
    case "completed":
      return task.status === "completed";
    case "failed":
      return hasFailedResultEvidence(task);
    case "queued":
      return task.status === "pending" || task.status === "running" || hasApprovalReviewEvidence(task);
    default:
      return true;
  }
}

export function getSharedTaskPresentationState(task: TaskEvidenceFields): SharedTaskPresentationState {
  switch (task.status) {
    case "pending_approval":
      return hasApprovalReviewEvidence(task) ? "approval" : "needs_sync";
    case "failed":
      return hasFailedResultEvidence(task) ? "failed" : "needs_sync";
    case "running":
      return "running";
    case "completed":
      return "completed";
    case "cancelled":
      return "cancelled";
    default:
      return "queued";
  }
}

export function getSharedTaskPresentation(task: TaskEvidenceFields) {
  const state = getSharedTaskPresentationState(task);
  return {
    state,
    label: PRESENTATION_LABELS[state],
    tone: PRESENTATION_TONES[state],
  };
}
