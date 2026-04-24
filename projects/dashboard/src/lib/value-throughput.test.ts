import { afterEach, describe, expect, it, vi } from "vitest";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { loadValueThroughputScorecard } from "@/lib/value-throughput";

describe("loadValueThroughputScorecard", () => {
  const cwdSpy = vi.spyOn(process, "cwd");
  let tempDir: string | null = null;

  afterEach(async () => {
    cwdSpy.mockRestore();
    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
      tempDir = null;
    }
  });

  it("marks the scorecard as degraded when the artifact reports degraded sections", async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-value-throughput-"));
    const reportDir = path.join(tempDir, "reports", "truth-inventory");
    await mkdir(reportDir, { recursive: true });
    await writeFile(
      path.join(reportDir, "value-throughput-scorecard.json"),
      JSON.stringify(
        {
          generated_at: "2026-04-19T00:00:00Z",
          degraded_sections: ["scheduled_jobs:Authentication required.", "backlog:fallback_to_ralph_queue_truth"],
          result_backed_completion_count: 0,
          review_backed_output_count: 0,
          stale_claim_count: 1,
          backlog_aging: {
            open_item_count: 3,
            by_family: [],
            by_project: [],
          },
          dispatch_to_result_latency: {
            completed_count: 0,
            average_hours: 0,
          },
          proposal_conversion: {
            proposal_backlog_count: 0,
            result_backed_completion_count: 0,
            review_backed_output_count: 0,
          },
          review_debt: {
            count: 0,
            oldest_age_hours: 0,
            by_family: [],
          },
          scheduled_execution: {
            queue_backed_jobs: 0,
            direct_control_jobs: 0,
            proposal_only_jobs: 0,
            blocked_jobs: 0,
            needs_sync_jobs: 0,
          },
          reconciliation: {
            issue_count: 1,
            repairable_count: 1,
            issues_by_type: {
              stale_terminal_task: 1,
            },
            issues: [],
          },
        },
        null,
        2,
      ),
      "utf-8",
    );
    cwdSpy.mockReturnValue(tempDir);

    const result = await loadValueThroughputScorecard();

    expect(result.status.available).toBe(true);
    expect(result.status.degraded).toBe(true);
    expect(result.status.detail).toContain("scheduled_jobs:Authentication required.");
    expect(result.scorecard?.degradedSections).toEqual([
      "scheduled_jobs:Authentication required.",
      "backlog:fallback_to_ralph_queue_truth",
    ]);
    expect(result.scorecard?.backlogAging.openItemCount).toBe(3);
    expect(result.scorecard?.staleClaimCount).toBe(1);
  });
});
