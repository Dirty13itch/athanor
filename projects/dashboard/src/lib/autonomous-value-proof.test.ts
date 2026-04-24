import { afterEach, describe, expect, it, vi } from "vitest";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { loadAutonomousValueProof } from "@/lib/autonomous-value-proof";

describe("loadAutonomousValueProof", () => {
  const cwdSpy = vi.spyOn(process, "cwd");
  let tempDir: string | null = null;

  afterEach(async () => {
    cwdSpy.mockRestore();
    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
      tempDir = null;
    }
  });

  it("loads accepted and disqualified autonomous value entries", async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-autonomous-value-"));
    const reportDir = path.join(tempDir, "reports", "truth-inventory");
    await mkdir(reportDir, { recursive: true });
    await writeFile(
      path.join(reportDir, "autonomous-value-proof.json"),
      JSON.stringify(
        {
          generated_at: "2026-04-20T04:20:00Z",
          accepted_entry_count: 3,
          accepted_operator_value_count: 2,
          accepted_product_value_count: 1,
          disqualified_entry_count: 1,
          failure_counts: {
            control_plane_only: 1,
          },
          latest_accepted_entry: {
            packet_id: "result-3",
            title: "Ship dashboard value proof",
            value_class: "product_value",
            deliverable_kind: "ui_change",
            beneficiary_surface: "dashboard",
            accepted_at: "2026-04-20T04:12:00Z",
          },
          accepted_entries: [
            {
              packet_id: "result-3",
              title: "Ship dashboard value proof",
              value_class: "product_value",
              deliverable_kind: "ui_change",
              beneficiary_surface: "dashboard",
              deliverable_refs: ["projects/dashboard/src/app/page.tsx"],
              accepted_at: "2026-04-20T04:12:00Z",
            },
          ],
          disqualified_entries: [
            {
              packet_id: "result-4",
              title: "Bookkeeping refresh",
              disqualification_reason: "control_plane_only",
            },
          ],
          stage_status: {
            operator_value: {
              required_count: 3,
              accepted_count: 2,
              distinct_family_count: 2,
              remaining_required: 1,
              met: false,
            },
            product_value: {
              required_count: 2,
              accepted_count: 1,
              visible_surface_count: 1,
              remaining_required: 1,
              met: false,
            },
          },
          degraded_sections: [],
        },
        null,
        2,
      ),
      "utf-8",
    );
    cwdSpy.mockReturnValue(tempDir);

    const result = await loadAutonomousValueProof();

    expect(result.status.available).toBe(true);
    expect(result.status.degraded).toBe(false);
    expect(result.proof?.acceptedOperatorValueCount).toBe(2);
    expect(result.proof?.acceptedProductValueCount).toBe(1);
    expect(result.proof?.latestAcceptedEntry?.beneficiarySurface).toBe("dashboard");
    expect(result.proof?.disqualifiedEntries[0]?.disqualificationReason).toBe("control_plane_only");
  });
});
