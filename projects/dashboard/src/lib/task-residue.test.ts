import { describe, expect, it } from "vitest";
import { extractTaskResidueSummary } from "./task-residue";

describe("extractTaskResidueSummary", () => {
  it("preserves canonical task residue fields from task stats", () => {
    const summary = extractTaskResidueSummary({
      total: 332,
      completed: 138,
      failed: 153,
      running: 0,
      pending: 0,
      pending_approval: 13,
      stale_lease: 21,
      stale_lease_actionable: 8,
      stale_lease_recovered_historical: 13,
      failed_actionable: 72,
      failed_historical_repaired: 81,
      failed_missing_detail: 0,
    });

    expect(summary.total).toBe(332);
    expect(summary.completed).toBe(138);
    expect(summary.failed).toBe(153);
    expect(summary.pending_approval).toBe(13);
    expect(summary.stale_lease).toBe(21);
    expect(summary.stale_lease_actionable).toBe(8);
    expect(summary.stale_lease_recovered_historical).toBe(13);
    expect(summary.failed_actionable).toBe(72);
    expect(summary.failed_historical_repaired).toBe(81);
    expect(summary.by_status.pending_approval).toBe(13);
    expect(summary.by_status.stale_lease).toBe(21);
  });

  it("falls back to by_status fields when top-level residue fields are absent", () => {
    const summary = extractTaskResidueSummary({
      total: 9,
      currently_running: 2,
      by_status: {
        completed: 3,
        failed: 4,
        running: 2,
        pending: 1,
        pending_approval: 5,
        stale_lease: 6,
      },
    });

    expect(summary.completed).toBe(3);
    expect(summary.running).toBe(2);
    expect(summary.pending).toBe(1);
    expect(summary.pending_approval).toBe(5);
    expect(summary.stale_lease).toBe(6);
    expect(summary.stale_lease_actionable).toBe(6);
    expect(summary.stale_lease_recovered_historical).toBe(0);
    expect(summary.currently_running).toBe(2);
    expect(summary.worker_running).toBe(true);
  });
});
