import type {
  BuilderFrontDoorSummary,
  BuilderKernelPressureStatus,
  BuilderKernelPressureSummary,
  ExecutionResultProjection,
  ExecutionReviewProjection,
} from "@/lib/contracts";

const ACTIONABLE_RESULT_STATUSES = new Set(["failed", "blocked", "cancelled"]);

function isBuilderPendingReview(review: ExecutionReviewProjection) {
  return review.family === "builder" && review.status === "pending";
}

function isBuilderActionableResult(result: ExecutionResultProjection) {
  return result.family === "builder" && ACTIONABLE_RESULT_STATUSES.has(result.status);
}

function currentSessionReviewCount(
  currentSessionId: string | null,
  reviews: ExecutionReviewProjection[],
) {
  if (!currentSessionId) return 0;
  return reviews.filter(
    (review) => review.owner_id === currentSessionId || review.related_task_id === currentSessionId,
  ).length;
}

function currentSessionResultCount(
  currentSessionId: string | null,
  results: ExecutionResultProjection[],
) {
  if (!currentSessionId) return 0;
  return results.filter((result) => result.owner_id === currentSessionId).length;
}

export function summarizeBuilderKernelPressure(
  builderFrontDoor: BuilderFrontDoorSummary,
  reviews: ExecutionReviewProjection[],
  results: ExecutionResultProjection[],
): BuilderKernelPressureSummary {
  const builderReviews = reviews.filter(isBuilderPendingReview);
  const builderResults = results.filter(isBuilderActionableResult);
  const currentSessionId = builderFrontDoor.current_session?.id ?? null;
  const currentSessionPendingReviewCount = currentSessionReviewCount(currentSessionId, builderReviews);
  const currentSessionActionableResultCount = currentSessionResultCount(currentSessionId, builderResults);
  const statusImpliesReview =
    (builderFrontDoor.current_session?.pending_approval_count ?? 0) > 0 ||
    builderFrontDoor.current_session?.status === "waiting_approval";
  const statusImpliesFailure =
    builderFrontDoor.current_session?.status === "failed" ||
    builderFrontDoor.current_session?.verification_status === "failed";
  const currentSessionNeedsSync = Boolean(
    builderFrontDoor.current_session &&
      ((statusImpliesReview && currentSessionPendingReviewCount === 0) ||
        (statusImpliesFailure && currentSessionActionableResultCount === 0)),
  );

  let currentSessionStatus: BuilderKernelPressureStatus = "ready";
  if (!builderFrontDoor.available) {
    currentSessionStatus = "offline";
  } else if (!builderFrontDoor.current_session) {
    currentSessionStatus = "ready";
  } else if (currentSessionNeedsSync) {
    currentSessionStatus = "needs_sync";
  } else if (currentSessionActionableResultCount > 0) {
    currentSessionStatus = "result_attention";
  } else if (currentSessionPendingReviewCount > 0) {
    currentSessionStatus = "review_required";
  } else if (["queued", "running", "planned"].includes(builderFrontDoor.current_session.status)) {
    currentSessionStatus = "active";
  }

  return {
    pending_review_count: builderReviews.length,
    actionable_result_count: builderResults.length,
    current_session_pending_review_count: currentSessionPendingReviewCount,
    current_session_actionable_result_count: currentSessionActionableResultCount,
    current_session_status: currentSessionStatus,
    current_session_needs_sync: currentSessionNeedsSync,
  };
}

export function getBuilderKernelSharedPressure(
  builderFrontDoor: Pick<
    BuilderFrontDoorSummary,
    "available" | "current_session" | "degraded"
  > & { shared_pressure?: BuilderKernelPressureSummary | null },
): BuilderKernelPressureSummary {
  if (builderFrontDoor.shared_pressure) {
    return builderFrontDoor.shared_pressure;
  }

  const currentSession = builderFrontDoor.current_session;
  const pendingReviewCount =
    currentSession && (currentSession.pending_approval_count > 0 || currentSession.status === "waiting_approval")
      ? Math.max(currentSession.pending_approval_count, 1)
      : 0;
  const actionableResultCount =
    currentSession && (currentSession.status === "failed" || currentSession.verification_status === "failed") ? 1 : 0;

  let currentSessionStatus: BuilderKernelPressureStatus = "ready";
  if (!builderFrontDoor.available) {
    currentSessionStatus = "offline";
  } else if (actionableResultCount > 0) {
    currentSessionStatus = "result_attention";
  } else if (pendingReviewCount > 0) {
    currentSessionStatus = "review_required";
  } else if (currentSession && ["queued", "running", "planned"].includes(currentSession.status)) {
    currentSessionStatus = "active";
  }

  return {
    pending_review_count: pendingReviewCount,
    actionable_result_count: actionableResultCount,
    current_session_pending_review_count: pendingReviewCount,
    current_session_actionable_result_count: actionableResultCount,
    current_session_status: currentSessionStatus,
    current_session_needs_sync: false,
  };
}

export function getBuilderKernelPressureTone(
  builderFrontDoor: Pick<BuilderFrontDoorSummary, "available" | "current_session" | "degraded"> & {
    shared_pressure?: BuilderKernelPressureSummary | null;
  },
) {
  const sharedPressure = getBuilderKernelSharedPressure(builderFrontDoor);
  if (builderFrontDoor.degraded) return "danger" as const;
  if (
    sharedPressure.current_session_status === "result_attention" ||
    sharedPressure.actionable_result_count > 0
  ) {
    return "danger" as const;
  }
  if (
    sharedPressure.current_session_status === "review_required" ||
    sharedPressure.current_session_status === "needs_sync" ||
    sharedPressure.pending_review_count > 0
  ) {
    return "warning" as const;
  }
  return "healthy" as const;
}

export function getBuilderKernelPressureLabel(
  builderFrontDoor: Pick<BuilderFrontDoorSummary, "available" | "current_session" | "degraded"> & {
    shared_pressure?: BuilderKernelPressureSummary | null;
  },
) {
  const sharedPressure = getBuilderKernelSharedPressure(builderFrontDoor);
  if (builderFrontDoor.degraded) return "feed degraded";
  switch (sharedPressure.current_session_status) {
    case "review_required":
      return "review pending";
    case "result_attention":
      return "result attention";
    case "needs_sync":
      return "needs sync";
    case "active":
      return builderFrontDoor.current_session?.status.replaceAll("_", " ") ?? "active";
    case "offline":
      return "offline";
    case "ready":
    default:
      return builderFrontDoor.current_session
        ? builderFrontDoor.current_session.status.replaceAll("_", " ")
        : "ready for intake";
  }
}
