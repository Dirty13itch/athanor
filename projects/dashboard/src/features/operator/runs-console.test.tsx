import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { RunsConsole } from "./runs-console";

const { requestJson } = vi.hoisted(() => ({
  requestJson: vi.fn(),
}));

vi.mock("@/features/workforce/helpers", () => ({
  requestJson,
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

describe("RunsConsole", () => {
  it("renders a degraded runs surface when the upstream feed is unavailable", async () => {
    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/operator/runs?status=running") {
        return {
          available: false,
          degraded: true,
          runs: [],
          count: 0,
        };
      }

      if (url === "/api/operator/summary") {
        return {
          runs: {
            total: 0,
            by_status: {},
          },
        };
      }

      return {};
    });

    render(<RunsConsole />, { wrapper: buildWrapper() });

    expect(await screen.findByRole("heading", { name: "Runs", level: 1 })).toBeInTheDocument();
    expect(await screen.findByText(/Runs feed degraded/i)).toBeInTheDocument();
    expect(screen.getByText(/Runs feed unavailable/i)).toBeInTheDocument();
  });
});
