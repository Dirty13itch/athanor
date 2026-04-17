import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { readSteadyStateFrontDoor } from "./operator-frontdoor";

const originalCwd = process.cwd();

afterEach(() => {
  process.chdir(originalCwd);
});

function makeWorkspace() {
  const root = mkdtempSync(path.join(tmpdir(), "athanor-frontdoor-"));
  const dashboardRoot = path.join(root, "projects", "dashboard");
  mkdirSync(dashboardRoot, { recursive: true });
  return { root, dashboardRoot };
}

function writeSteadyStateJson(targetPath: string, overrides: Record<string, unknown> = {}) {
  mkdirSync(path.dirname(targetPath), { recursive: true });
  writeFileSync(
    targetPath,
    JSON.stringify({
      generated_at: "2026-04-16T00:00:00.000Z",
      closure_state: "repo_safe_complete",
      operator_mode: "steady_state_monitoring",
      intervention_label: "No action needed",
      intervention_level: "no_action_needed",
      intervention_summary: "Queue is moving without operator intervention.",
      needs_you: false,
      next_operator_action: "Keep monitoring.",
      queue_dispatchable: 2,
      queue_total: 5,
      suppressed_task_count: 3,
      runtime_packet_count: 0,
      current_work: {
        task_title: "Cheap Bulk Cloud",
        provider_label: "deepseek_api",
        lane_family: "capacity_truth_repair",
      },
      next_up: {
        task_title: "Letta Memory Plane",
        provider_label: "Athanor Local",
        lane_family: "memory_plane",
      },
      ...overrides,
    }),
    "utf-8",
  );
}

describe("readSteadyStateFrontDoor", () => {
  it("annotates workspace report provenance when the local report exists", async () => {
    const { dashboardRoot } = makeWorkspace();
    writeSteadyStateJson(path.join(dashboardRoot, "reports", "truth-inventory", "steady-state-status.json"));
    process.chdir(dashboardRoot);

    const result = await readSteadyStateFrontDoor();

    expect(result?.sourceKind).toBe("workspace_report");
    expect(result?.sourcePath).toBe(
      path.join(dashboardRoot, "reports", "truth-inventory", "steady-state-status.json"),
    );
  });

  it("annotates repo-root fallback provenance when only the repo-level report exists", async () => {
    const { root, dashboardRoot } = makeWorkspace();
    writeSteadyStateJson(path.join(root, "reports", "truth-inventory", "steady-state-status.json"));
    process.chdir(dashboardRoot);

    const result = await readSteadyStateFrontDoor();

    expect(result?.sourceKind).toBe("repo_root_fallback");
    expect(result?.sourcePath).toBe(
      path.join(root, "reports", "truth-inventory", "steady-state-status.json"),
    );
  });

  it("stops on invalid readable input instead of silently falling through to another candidate", async () => {
    const { root, dashboardRoot } = makeWorkspace();
    mkdirSync(path.join(dashboardRoot, "reports", "truth-inventory"), { recursive: true });
    writeFileSync(
      path.join(dashboardRoot, "reports", "truth-inventory", "steady-state-status.json"),
      "{not-json",
      "utf-8",
    );
    writeSteadyStateJson(path.join(root, "reports", "truth-inventory", "steady-state-status.json"));
    process.chdir(dashboardRoot);

    await expect(readSteadyStateFrontDoor()).rejects.toThrow(/Invalid steady-state front door/);
  });
});
