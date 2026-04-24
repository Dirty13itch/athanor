import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ModelObservatory } from "./model-observatory";

const { getGpuSnapshot, getModelGovernance, requestJson, useOperatorSessionStatus, isOperatorSessionLocked } = vi.hoisted(() => ({
  getGpuSnapshot: vi.fn(),
  getModelGovernance: vi.fn(),
  requestJson: vi.fn(),
  useOperatorSessionStatus: vi.fn(),
  isOperatorSessionLocked: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  getGpuSnapshot,
  getModelGovernance,
}));

vi.mock("@/features/workforce/helpers", () => ({
  requestJson,
}));

vi.mock("@/lib/operator-session", () => ({
  useOperatorSessionStatus,
  isOperatorSessionLocked,
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

describe("ModelObservatory", () => {
  it("keeps provider economics as a compact handoff to Subscriptions", async () => {
    useOperatorSessionStatus.mockReturnValue({ isPending: false });
    isOperatorSessionLocked.mockReturnValue(false);
    getGpuSnapshot.mockResolvedValue({ gpus: [] });
    getModelGovernance.mockResolvedValue({
      capability_intelligence: {
        implementation: { subject_id: "openai_codex", capability_score: 91 },
        audit: { subject_id: "google_gemini", capability_score: 89 },
        local_endpoint: { subject_id: "foundry-coder-lane", capability_score: 95 },
        degraded_subject_count: 1,
      },
    });

    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/routing/log?limit=20") {
        return {
          entries: [
            {
              task_id: "task-abc",
              policy_class: "local_only",
              provider: "deepseek",
              outcome: "success",
            },
          ],
        };
      }

      return {};
    });

    render(
      <ModelObservatory
        localModels={[
          {
            alias: "foundry-coder",
            litellmAlias: "coder",
            name: "Foundry Coder",
            node: "Foundry",
            nodeId: "foundry",
            description: "Local coding model",
          },
        ]}
      />,
      { wrapper: buildWrapper() },
    );

    expect(await screen.findByRole("heading", { name: /Model Observatory/i })).toBeInTheDocument();
    expect(screen.getByText(/Provider economics/i, { selector: "[data-slot='card-title']" })).toBeInTheDocument();
    expect(screen.getByText(/Capability leaders/i, { selector: "[data-slot='card-title']" })).toBeInTheDocument();
    expect(await screen.findByText(/openai codex/i)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Open Subscriptions/i })).toHaveLength(2);
    expect(screen.queryByText(/Subscription CLIs/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Routing Intelligence/i)).toBeInTheDocument();
    expect(screen.getByText(/Agent Assignment Matrix/i)).toBeInTheDocument();
  });
});
