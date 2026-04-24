import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DigestConsole } from "./digest-console";

const { requestJson, postWithoutBody, postJson, useOperatorSessionStatus, isOperatorSessionLocked } =
  vi.hoisted(() => ({
    requestJson: vi.fn(),
    postWithoutBody: vi.fn(),
    postJson: vi.fn(),
    useOperatorSessionStatus: vi.fn(),
    isOperatorSessionLocked: vi.fn(),
  }));

vi.mock("@/features/workforce/helpers", () => ({
  requestJson,
  postWithoutBody,
  postJson,
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

describe("DigestConsole", () => {
  beforeEach(() => {
    useOperatorSessionStatus.mockReturnValue({ isPending: false });
    isOperatorSessionLocked.mockReturnValue(false);
    postWithoutBody.mockResolvedValue(undefined);
    postJson.mockResolvedValue(undefined);
  });

  it("reads pending approvals from shared execution reviews and approves through the shared review route", async () => {
    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/execution/reviews?status=pending") {
        return {
          reviews: [
            {
              id: "review-1",
              family: "bootstrap_takeover",
              source: "bootstrap_program",
              owner_kind: "program",
              owner_id: "launch-readiness-bootstrap",
              related_run_id: "bootstrap-program:launch-readiness-bootstrap",
              related_task_id: "persist-04-activation-cutover",
              requested_action: "approve",
              privilege_class: "admin",
              reason: "Approve durable persistence cutover.",
              status: "pending",
              requested_at: 1_710_000_000,
              task_prompt: "Approve durable persistence cutover.",
              task_agent_id: "durable_persistence_activation",
              task_priority: "high",
              task_status: "waiting_approval",
              deep_link:
                "/bootstrap?program=launch-readiness-bootstrap&slice=persist-04-activation-cutover",
              metadata: {},
            },
          ],
          count: 1,
        };
      }

      if (url === "/api/operator/runs?status=completed&limit=20") {
        return { runs: [] };
      }

      if (url === "/api/operator/summary") {
        return {
          projects: {
            stalled_total: 0,
            stalled_preview: [],
          },
        };
      }

      return {};
    });

    render(<DigestConsole />, { wrapper: buildWrapper() });

    expect(await screen.findByRole("heading", { name: /Morning Digest/i })).toBeInTheDocument();
    expect(await screen.findByText(/Approve durable persistence cutover\./i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^Approve$/i }));

    await waitFor(() => {
      expect(postWithoutBody).toHaveBeenCalledWith("/api/execution/reviews/review-1/approve");
    });
  });
});
