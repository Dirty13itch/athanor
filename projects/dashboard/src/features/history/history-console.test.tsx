import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getFixtureHistorySnapshot } from "@/lib/dashboard-fixtures";
import { HistoryConsole } from "./history-console";

const { getHistory, getSearchValue, setSearchValue } = vi.hoisted(() => ({
  getHistory: vi.fn(),
  getSearchValue: vi.fn(),
  setSearchValue: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getHistory,
  };
});

vi.mock("@/lib/url-state", () => ({
  useUrlState: () => ({
    getSearchValue,
    setSearchValue,
  }),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/activity",
  useSearchParams: () => new URLSearchParams(),
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

describe("HistoryConsole", () => {
  beforeEach(() => {
    setSearchValue.mockReset();
    const snapshot = getFixtureHistorySnapshot();
    snapshot.activity[0] = {
      ...snapshot.activity[0],
      id: "activity-explicit-result",
      actionType: "review_result_packet",
      inputSummary: "Explicit result-backed history item.",
      outputSummary: "The kernel emitted a result packet without a related task row.",
      relatedTaskId: null,
      status: "failed",
      // exercise explicit kernel ids instead of status-based inference
      resultId: "builder-result:history-explicit-result",
      reviewId: null,
    } as typeof snapshot.activity[0] & { reviewId: string | null; resultId: string | null };
    getHistory.mockResolvedValue(snapshot);
    getSearchValue.mockImplementation((key: string, fallback: string) => {
      if (key === "selection") {
        return "activity-explicit-result";
      }
      return fallback;
    });
  });

  it("uses explicit history result ids for failed-item presentation and review deep links", async () => {
    render(<HistoryConsole initialSnapshot={await getHistory()} variant="activity" />, {
      wrapper: buildWrapper(),
    });

    expect(await screen.findByText("Activity Feed")).toBeInTheDocument();
    expect(screen.getAllByText("Failed").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /Review item/i })).toHaveAttribute(
      "href",
      "/review?selection=builder-result%3Ahistory-explicit-result",
    );
  });
});
