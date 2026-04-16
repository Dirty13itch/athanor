export interface TaskResidueSummary {
  total: number;
  completed: number;
  running: number;
  failed: number;
  pending: number;
  pending_approval: number;
  stale_lease: number;
  stale_lease_actionable: number;
  stale_lease_recovered_historical: number;
  failed_actionable: number;
  failed_historical_repaired: number;
  failed_missing_detail: number;
  currently_running: number;
  worker_running: boolean;
  by_status: {
    completed: number;
    running: number;
    failed: number;
    pending: number;
    pending_approval: number;
    stale_lease: number;
  };
}

function toCount(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

export function extractTaskResidueSummary(source: unknown): TaskResidueSummary {
  const record = asRecord(source);
  const byStatus = asRecord(record.by_status);

  const completed = toCount(record.completed ?? byStatus.completed);
  const running = toCount(record.running ?? byStatus.running ?? record.currently_running);
  const failed = toCount(record.failed ?? byStatus.failed);
  const pending = toCount(record.pending ?? byStatus.pending ?? byStatus.queued);
  const pendingApproval = toCount(record.pending_approval ?? byStatus.pending_approval);
  const staleLease = toCount(record.stale_lease ?? byStatus.stale_lease);
  const staleLeaseActionable = toCount(record.stale_lease_actionable ?? staleLease);
  const staleLeaseRecoveredHistorical = toCount(record.stale_lease_recovered_historical);
  const failedActionable = toCount(record.failed_actionable);
  const failedHistoricalRepaired = toCount(record.failed_historical_repaired);
  const failedMissingDetail = toCount(record.failed_missing_detail);
  const currentlyRunning = toCount(record.currently_running ?? running);
  const workerRunning = Boolean(record.worker_running ?? currentlyRunning > 0);

  return {
    total: toCount(record.total),
    completed,
    running,
    failed,
    pending,
    pending_approval: pendingApproval,
    stale_lease: staleLease,
    stale_lease_actionable: staleLeaseActionable,
    stale_lease_recovered_historical: staleLeaseRecoveredHistorical,
    failed_actionable: failedActionable,
    failed_historical_repaired: failedHistoricalRepaired,
    failed_missing_detail: failedMissingDetail,
    currently_running: currentlyRunning,
    worker_running: workerRunning,
    by_status: {
      completed,
      running,
      failed,
      pending,
      pending_approval: pendingApproval,
      stale_lease: staleLease,
    },
  };
}
