import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { loadCapabilityPilotReadiness } from "./capability-pilot-readiness";

const originalCwd = process.cwd();

afterEach(() => {
  process.chdir(originalCwd);
});

function makeWorkspace() {
  const root = mkdtempSync(path.join(tmpdir(), "athanor-pilot-readiness-"));
  const dashboardRoot = path.join(root, "projects", "dashboard");
  mkdirSync(path.join(dashboardRoot, "src", "generated"), { recursive: true });
  return { root, dashboardRoot };
}

function writeMasterAtlas(targetPath: string) {
  writeFileSync(
    targetPath,
    JSON.stringify({
      generated_at: "2026-04-16T00:00:00.000Z",
      capability_pilot_readiness: {
        records: [
          {
            capability_id: "letta-memory-plane",
            label: "Letta Memory Plane",
            host_id: "desk",
            readiness_state: "blocked",
            proof_tier: "operator_smoke_plus_formal_scaffold",
            blocking_reasons: ["missing_packet", "missing_env:LETTA_API_KEY"],
            command_checks: [
              {
                command: "letta",
                available_locally: true,
                inventory_status: "installed",
                inventory_version: "0.1.0",
                local_path: "/usr/local/bin/letta",
              },
            ],
            packet_path: "C:/athanor-devstack/docs/promotion-packets/letta-memory-plane.md",
            latest_eval_status: "passed",
            latest_eval_outcome: "ready",
            latest_eval_at: "2026-04-12T16:44:59.399550+00:00",
            formal_preflight_status: "blocked",
            formal_preflight_at: "2026-04-12T16:44:59.692850+00:00",
            formal_preflight_blocker_class: "env_wiring",
            formal_preflight_blocking_reasons: ["missing_env:LETTA_API_KEY"],
            formal_preflight_missing_env_vars: ["LETTA_API_KEY"],
            formal_preflight_missing_commands: [],
            formal_preflight_missing_fixture_files: [],
            formal_preflight_missing_result_files: [],
            next_action: "Wire LETTA_API_KEY and run the bounded continuity benchmark.",
            next_formal_gate: "Wire the required formal-eval env vars: LETTA_API_KEY.",
          },
          {
            capability_id: "openhands-bounded-worker-lane",
            label: "OpenHands Bounded Worker Lane",
            host_id: "desk",
            readiness_state: "blocked",
            proof_tier: "blocked",
            blocking_reasons: ["missing_command:openhands"],
            command_checks: [],
            packet_path: "C:/athanor-devstack/docs/promotion-packets/openhands-bounded-worker-lane.md",
            latest_eval_status: "blocked",
            latest_eval_outcome: "blocked",
            latest_eval_at: "2026-04-12T16:44:59.403511+00:00",
            formal_preflight_status: "blocked",
            formal_preflight_at: "2026-04-12T16:44:59.403511+00:00",
            formal_preflight_blocker_class: "missing_command",
            formal_preflight_blocking_reasons: ["missing_command:openhands"],
            formal_preflight_missing_commands: ["openhands"],
            formal_preflight_missing_env_vars: ["OPENAI_API_KEY"],
            formal_preflight_missing_fixture_files: [],
            formal_preflight_missing_result_files: [],
            next_action: "Expose the OpenHands command on DESK.",
            next_formal_gate: "Install or expose openhands on the preferred pilot host.",
          },
          {
            capability_id: "agent-governance-toolkit-policy-plane",
            label: "Agent Governance Toolkit Policy Plane",
            host_id: "desk",
            readiness_state: "blocked",
            proof_tier: "formal_eval_failed",
            blocking_reasons: ["missing_packet"],
            command_checks: [],
            packet_path: "C:/athanor-devstack/docs/promotion-packets/agent-governance-toolkit-policy-plane.md",
            formal_eval_status: "failed",
            formal_eval_at: "2026-04-12T16:44:59.693341+00:00",
            formal_eval_decision_reason: "manual_review_rejected",
            manual_review_outcome: "rejected_as_redundant_for_current_stack",
            manual_review_summary: "Current narrow approval-held mutation bundle does not prove non-duplicative operational value.",
            next_action: "Leave this lane below adapter work unless a second protocol-boundary scenario proves unique value.",
            next_formal_gate: "Keep below adapter work unless a second protocol-boundary scenario shows non-duplicative value.",
          },
        ],
      },
    }),
    "utf-8",
  );
}

describe("loadCapabilityPilotReadiness", () => {
  it("loads the three pilot readiness lanes from the workspace master atlas feed", async () => {
    const { dashboardRoot } = makeWorkspace();
    writeMasterAtlas(path.join(dashboardRoot, "src", "generated", "master-atlas.json"));
    process.chdir(dashboardRoot);

    const snapshot = await loadCapabilityPilotReadiness();

    expect(snapshot.available).toBe(true);
    expect(snapshot.degraded).toBe(false);
    expect(snapshot.sourceKind).toBe("workspace_generated_atlas");
    expect(snapshot.records).toHaveLength(3);
    expect(snapshot.records.map((record) => record.capabilityId)).toEqual([
      "letta-memory-plane",
      "openhands-bounded-worker-lane",
      "agent-governance-toolkit-policy-plane",
    ]);
    expect(snapshot.summary).toMatchObject({
      total: 3,
      blocked: 3,
      formalEvalComplete: 0,
      formalEvalFailed: 0,
      manualReviewPending: 0,
      readyForFormalEval: 0,
      operatorSmokeOnly: 0,
      scaffoldOnly: 0,
    });
    expect(snapshot.records[0]).toMatchObject({
      capabilityId: "letta-memory-plane",
      readinessState: "blocked",
      formalPreflightMissingEnvVars: ["LETTA_API_KEY"],
    });
    expect(snapshot.records[1]).toMatchObject({
      capabilityId: "openhands-bounded-worker-lane",
      formalPreflightMissingCommands: ["openhands"],
    });
    expect(snapshot.records[2]).toMatchObject({
      capabilityId: "agent-governance-toolkit-policy-plane",
      manualReviewOutcome: "rejected_as_redundant_for_current_stack",
    });
  });
});
