import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { requestJson } from "@/features/workforce/helpers";
import { PilotReadinessBlock } from "./pilot-readiness-block";

vi.mock("@/features/workforce/helpers", () => ({
  requestJson: vi.fn(),
}));

function buildWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe("PilotReadinessBlock", () => {
  it("renders the operator pilot lanes with explicit blockers and gates", async () => {
    vi.mocked(requestJson).mockResolvedValue({
      generatedAt: "2026-04-16T15:11:19.861884+00:00",
      available: true,
      degraded: false,
      detail: null,
      sourceKind: "workspace_generated_atlas",
      sourcePath: "/mnt/c/Athanor/projects/dashboard/src/generated/master-atlas.json",
      summary: {
        total: 3,
        formalEvalComplete: 0,
        formalEvalFailed: 0,
        manualReviewPending: 0,
        readyForFormalEval: 0,
        operatorSmokeOnly: 0,
        scaffoldOnly: 0,
        blocked: 3,
      },
      records: [
        {
          capabilityId: "letta-memory-plane",
          label: "Letta Memory Plane",
          laneStatus: null,
          capabilityStage: null,
          hostId: "desk",
          readinessState: "blocked",
          proofTier: "operator_smoke_plus_formal_scaffold",
          blockingReasons: ["missing_packet", "missing_env:LETTA_API_KEY"],
          commandChecks: [],
          packetPath: "C:/athanor-devstack/docs/promotion-packets/letta-memory-plane.md",
          latestEvalRunId: null,
          latestEvalStatus: null,
          latestEvalOutcome: null,
          latestEvalAt: null,
          formalEvalStatus: null,
          formalEvalAt: null,
          formalEvalDecisionReason: null,
          formalEvalPrimaryFailureHint: null,
          formalPreflightStatus: null,
          formalPreflightAt: null,
          formalPreflightBlockerClass: "env_wiring",
          formalPreflightBlockingReasons: ["missing_env:LETTA_API_KEY"],
          formalPreflightMissingCommands: [],
          formalPreflightMissingEnvVars: ["LETTA_API_KEY"],
          formalPreflightMissingFixtureFiles: [],
          formalPreflightMissingResultFiles: [],
          manualReviewOutcome: null,
          manualReviewSummary: null,
          nextAction: "Wire LETTA_API_KEY, run the bounded continuity benchmark, and keep replayability and pruning explicit.",
          nextFormalGate: "Wire the required formal-eval env vars: `LETTA_API_KEY`.",
          formalRunnerSupport: null,
        },
        {
          capabilityId: "openhands-bounded-worker-lane",
          label: "OpenHands Bounded Worker Lane",
          laneStatus: null,
          capabilityStage: null,
          hostId: "desk",
          readinessState: "blocked",
          proofTier: "blocked",
          blockingReasons: [
            "missing_command:openhands",
            "missing_packet",
            "missing_env:OPENAI_API_KEY",
            "missing_env:PROMPTFOO_OPENHANDS_CMD",
            "missing_env:PROMPTFOO_OPENHANDS_ARGS_JSON",
          ],
          commandChecks: [],
          packetPath: "C:/athanor-devstack/docs/promotion-packets/openhands-bounded-worker-lane.md",
          latestEvalRunId: null,
          latestEvalStatus: null,
          latestEvalOutcome: null,
          latestEvalAt: null,
          formalEvalStatus: null,
          formalEvalAt: null,
          formalEvalDecisionReason: null,
          formalEvalPrimaryFailureHint: null,
          formalPreflightStatus: null,
          formalPreflightAt: null,
          formalPreflightBlockerClass: "missing_command",
          formalPreflightBlockingReasons: ["missing_command:openhands"],
          formalPreflightMissingCommands: ["openhands"],
          formalPreflightMissingEnvVars: ["OPENAI_API_KEY"],
          formalPreflightMissingFixtureFiles: [],
          formalPreflightMissingResultFiles: [],
          manualReviewOutcome: null,
          manualReviewSummary: null,
          nextAction: "Expose the OpenHands command on DESK, clear the worker env wiring, and run the bounded-worker eval.",
          nextFormalGate: "Install or expose `openhands` on the preferred pilot host.",
          formalRunnerSupport: null,
        },
        {
          capabilityId: "agent-governance-toolkit-policy-plane",
          label: "Agent Governance Toolkit Policy Plane",
          laneStatus: null,
          capabilityStage: null,
          hostId: "desk",
          readinessState: "blocked",
          proofTier: "formal_eval_failed",
          blockingReasons: ["missing_packet"],
          commandChecks: [],
          packetPath: "C:/athanor-devstack/docs/promotion-packets/agent-governance-toolkit-policy-plane.md",
          latestEvalRunId: null,
          latestEvalStatus: null,
          latestEvalOutcome: null,
          latestEvalAt: null,
          formalEvalStatus: "failed",
          formalEvalAt: null,
          formalEvalDecisionReason: null,
          formalEvalPrimaryFailureHint: null,
          formalPreflightStatus: null,
          formalPreflightAt: null,
          formalPreflightBlockerClass: null,
          formalPreflightBlockingReasons: [],
          formalPreflightMissingCommands: [],
          formalPreflightMissingEnvVars: [],
          formalPreflightMissingFixtureFiles: [],
          formalPreflightMissingResultFiles: [],
          manualReviewOutcome: "rejected_as_redundant_for_current_stack",
          manualReviewSummary: "Current narrow approval-held mutation bundle does not prove non-duplicative operational value.",
          nextAction: "Leave this lane below adapter work on the current manual review, and only reopen it if a second protocol-boundary scenario proves unique value over native Athanor policy.",
          nextFormalGate: "Keep this lane below adapter work unless a second protocol-boundary scenario shows non-duplicative value over native Athanor policy.",
          formalRunnerSupport: null,
        },
      ],
    });

    render(<PilotReadinessBlock />, { wrapper: buildWrapper() });

    expect(await screen.findByRole("heading", { name: /Letta, OpenHands, AGT/i })).toBeInTheDocument();
    expect(await screen.findByText(/3 lanes/)).toBeInTheDocument();
    expect(await screen.findByText(/3 blocked/)).toBeInTheDocument();

    const lettaCard = (await screen.findByText("Letta Memory Plane")).closest("article");
    const openHandsCard = (await screen.findByText("OpenHands Bounded Worker Lane")).closest("article");
    const agtCard = (await screen.findByText("Agent Governance Toolkit Policy Plane")).closest("article");

    expect(lettaCard).toBeTruthy();
    expect(openHandsCard).toBeTruthy();
    expect(agtCard).toBeTruthy();

    if (!lettaCard || !openHandsCard || !agtCard) return;

    expect(within(lettaCard).getByText(/env LETTA_API_KEY/i)).toBeInTheDocument();
    expect(within(lettaCard).getByText(/Wire LETTA_API_KEY, run the bounded continuity benchmark, and keep replayability and pruning explicit\./i)).toBeInTheDocument();
    expect(within(lettaCard).getByText(/Wire the required formal-eval env vars: `LETTA_API_KEY`\./i)).toBeInTheDocument();

    expect(within(openHandsCard).getByText(/command openhands/i)).toBeInTheDocument();
    expect(within(openHandsCard).getByText(/OPENAI_API_KEY/i)).toBeInTheDocument();
    expect(within(openHandsCard).getByText(/Install or expose `openhands` on the preferred pilot host\./i)).toBeInTheDocument();

    expect(within(agtCard).getByText(/manual review rejected/i)).toBeInTheDocument();
    expect(within(agtCard).getByText(/Leave this lane below adapter work on the current manual review/i)).toBeInTheDocument();
    expect(within(agtCard).getByText(/Keep this lane below adapter work unless a second protocol-boundary scenario shows non-duplicative value over native Athanor policy\./i)).toBeInTheDocument();
  });
});
