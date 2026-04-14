import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { BacklogConsole } from "./backlog-console";

const { requestJson, postJson } = vi.hoisted(() => ({
  requestJson: vi.fn(),
  postJson: vi.fn(),
}));

vi.mock("@/features/workforce/helpers", () => ({
  requestJson,
  postJson,
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

describe("BacklogConsole", () => {
  it("renders a degraded backlog surface when the upstream feed is unavailable", async () => {
    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/operator/backlog?status=ready") {
        return {
          available: false,
          degraded: true,
          backlog: [],
          count: 0,
        };
      }

      if (url === "/api/operator/summary") {
        return {
          backlog: {
            total: 0,
            by_status: {},
          },
        };
      }

      return {};
    });

    render(<BacklogConsole />, { wrapper: buildWrapper() });

    expect(await screen.findByRole("heading", { name: "Backlog", level: 1 })).toBeInTheDocument();
    expect(await screen.findByText(/Backlog feed degraded/i)).toBeInTheDocument();
    expect(screen.getByText(/Backlog feed unavailable/i)).toBeInTheDocument();
  });

  it("supports an all-status deep link so captured governed work is visible from routing", async () => {
    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/operator/backlog") {
        return {
          backlog: [
            {
              id: "backlog-d13e5ae5",
              title: "Dispatch and Work-Economy Closure",
              prompt: "Advance governed dispatch closure.",
              owner_agent: "coding-agent",
              work_class: "system_improvement",
              priority: 1,
              status: "captured",
              approval_mode: "none",
              blocking_reason: "",
              updated_at: 1776110558,
            },
          ],
          count: 1,
        };
      }

      if (url === "/api/operator/summary") {
        return {
          backlog: {
            total: 1,
            by_status: { captured: 1 },
          },
        };
      }

      return {};
    });

    render(<BacklogConsole initialStatus="all" />, { wrapper: buildWrapper() });

    expect(await screen.findByText(/Dispatch and Work-Economy Closure/i)).toBeInTheDocument();
    expect(requestJson).toHaveBeenCalledWith("/api/operator/backlog");
  });
});
