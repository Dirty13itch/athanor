import { describe, expect, it } from "vitest";
import {
  getSharedTaskPresentation,
  getSharedTaskPresentationState,
  hasApprovalReviewEvidence,
  hasFailedResultEvidence,
  matchesSharedTaskFilter,
} from "@/lib/task-filter-evidence";

describe("task filter evidence", () => {
  const approvalBackedTask = {
    status: "pending_approval" as const,
    reviewId: "approval:task-1",
    resultId: null,
  };

  const staleApprovalTask = {
    status: "pending_approval" as const,
    reviewId: null,
    resultId: null,
  };

  const failedBackedTask = {
    status: "failed" as const,
    reviewId: null,
    resultId: "builder-result:task-2",
  };

  const staleFailedTask = {
    status: "failed" as const,
    reviewId: null,
    resultId: null,
  };

  const pendingTask = {
    status: "pending" as const,
    reviewId: null,
    resultId: null,
  };

  it("requires explicit review evidence for approval-held filters", () => {
    expect(hasApprovalReviewEvidence(approvalBackedTask)).toBe(true);
    expect(hasApprovalReviewEvidence(staleApprovalTask)).toBe(false);
    expect(matchesSharedTaskFilter(approvalBackedTask, "approval")).toBe(true);
    expect(matchesSharedTaskFilter(staleApprovalTask, "approval")).toBe(false);
  });

  it("requires explicit result evidence for failed filters", () => {
    expect(hasFailedResultEvidence(failedBackedTask)).toBe(true);
    expect(hasFailedResultEvidence(staleFailedTask)).toBe(false);
    expect(matchesSharedTaskFilter(failedBackedTask, "failed")).toBe(true);
    expect(matchesSharedTaskFilter(staleFailedTask, "failed")).toBe(false);
  });

  it("keeps queued filters on live work and evidence-backed approval holds only", () => {
    expect(matchesSharedTaskFilter(pendingTask, "queued")).toBe(true);
    expect(matchesSharedTaskFilter(approvalBackedTask, "queued")).toBe(true);
    expect(matchesSharedTaskFilter(staleApprovalTask, "queued")).toBe(false);
    expect(matchesSharedTaskFilter(failedBackedTask, "queued")).toBe(false);
  });

  it("downgrades stale approval and failed states to needs-sync presentation", () => {
    expect(getSharedTaskPresentationState(approvalBackedTask)).toBe("approval");
    expect(getSharedTaskPresentationState(failedBackedTask)).toBe("failed");
    expect(getSharedTaskPresentationState(staleApprovalTask)).toBe("needs_sync");
    expect(getSharedTaskPresentationState(staleFailedTask)).toBe("needs_sync");
    expect(getSharedTaskPresentation(staleApprovalTask)).toEqual({
      state: "needs_sync",
      label: "Needs sync",
      tone: "warning",
    });
  });
});
