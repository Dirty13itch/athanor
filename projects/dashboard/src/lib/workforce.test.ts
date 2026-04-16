import { afterEach, describe, expect, it } from "vitest";
import { overviewSnapshotSchema, workforceSnapshotResponseSchema } from "@/lib/contracts";
import { getOverviewSnapshot, getWorkforceSnapshot } from "@/lib/dashboard-data";

const originalFixtureMode = process.env.DASHBOARD_FIXTURE_MODE;

afterEach(() => {
  if (originalFixtureMode === undefined) {
    delete process.env.DASHBOARD_FIXTURE_MODE;
  } else {
    process.env.DASHBOARD_FIXTURE_MODE = originalFixtureMode;
  }
});

describe("workforce snapshot", () => {
  it("returns the expanded workforce contract in fixture mode", async () => {
    process.env.DASHBOARD_FIXTURE_MODE = "1";

    const snapshot = await getWorkforceSnapshot();
    expect(() => workforceSnapshotResponseSchema.parse(snapshot)).not.toThrow();
    expect(snapshot.trust.length).toBeGreaterThan(0);
    expect(snapshot.subscriptions.length).toBeGreaterThan(0);
    expect(snapshot.conventions.proposed.length).toBeGreaterThan(0);
    expect(snapshot.improvement?.totalProposals).toBeGreaterThan(0);
  });

  it("embeds workforce state into the overview snapshot", async () => {
    process.env.DASHBOARD_FIXTURE_MODE = "1";

    const snapshot = await getOverviewSnapshot();
    expect(() => overviewSnapshotSchema.parse(snapshot)).not.toThrow();
    expect(snapshot.workforce.summary.activeProjects).toBeGreaterThan(0);
    expect(snapshot.workforce.projects.some((project) => project.firstClass)).toBe(true);
  });
});
