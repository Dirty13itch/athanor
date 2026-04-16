import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { GallerySnapshot } from "@/lib/contracts";
import { GalleryConsole } from "./gallery-console";

const { getGalleryOverview, getSearchValue, setSearchValue, getRating, setRating } = vi.hoisted(() => ({
  getGalleryOverview: vi.fn(),
  getSearchValue: vi.fn(),
  setSearchValue: vi.fn(),
  getRating: vi.fn(),
  setRating: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getGalleryOverview,
  };
});

vi.mock("@/lib/url-state", () => ({
  useUrlState: () => ({
    getSearchValue,
    setSearchValue,
  }),
}));

vi.mock("./use-gallery-ratings", () => ({
  useGalleryRatings: () => ({
    getRating,
    setRating,
  }),
}));

function buildWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

const snapshot: GallerySnapshot = {
  generatedAt: "2026-03-27T01:00:00.000Z",
  queueRunning: 1,
  queuePending: 2,
  deviceName: "NVIDIA GeForce RTX 5090",
  vramUsedGiB: 18.4,
  vramTotalGiB: 32,
  items: [
    {
      id: "gallery-1",
      prompt: "Cinematic portrait of a queen in dark armor.",
      outputPrefix: "EoBQ/character",
      timestamp: 1_743_035_200,
      outputImages: [{ filename: "queen-a.webp", subfolder: "EoBQ/character", type: "output" }],
    },
    {
      id: "gallery-2",
      prompt: "Wide throne room scene with drifting ash.",
      outputPrefix: "EoBQ/scene",
      timestamp: 1_743_031_600,
      outputImages: [{ filename: "throne-room.webp", subfolder: "EoBQ/scene", type: "output" }],
    },
  ],
};

describe("GalleryConsole", () => {
  beforeEach(() => {
    getGalleryOverview.mockReset();
    getSearchValue.mockReset();
    setSearchValue.mockReset();
    getRating.mockReset();
    setRating.mockReset();

    getSearchValue.mockImplementation((key: string, fallback: string) => fallback);
    getGalleryOverview.mockResolvedValue(snapshot);
    getRating.mockReturnValue(undefined);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders the gallery operator surface and drives compare and batch actions", async () => {
    render(<GalleryConsole initialSnapshot={snapshot} />, { wrapper: buildWrapper() });

    expect(await screen.findByRole("heading", { name: "Gallery" })).toBeInTheDocument();
    expect(await screen.findByText("Queue")).toBeInTheDocument();
    expect(await screen.findByText("RTX 5090")).toBeInTheDocument();
    expect(await screen.findByText("Images")).toBeInTheDocument();
    expect(await screen.findByText("Video + Scene")).toBeInTheDocument();
    expect(await screen.findByText("Cinematic portrait of a queen in dark armor.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Compare/i }));
    fireEvent.click(screen.getByRole("button", { name: /Cinematic portrait of a queen in dark armor\./i }));
    fireEvent.click(screen.getByRole("button", { name: /Wide throne room scene with drifting ash\./i }));

    expect(await screen.findByText("Comparison (2/2)")).toBeInTheDocument();
    expect(screen.getAllByText("Cinematic portrait of a queen in dark armor.").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Wide throne room scene with drifting ash.").length).toBeGreaterThanOrEqual(2);

    fireEvent.click(screen.getByRole("button", { name: /Batch/i }));
    fireEvent.click(screen.getByRole("button", { name: /Cinematic portrait of a queen in dark armor\./i }));
    fireEvent.click(screen.getAllByRole("button", { name: /Select All/i })[0]);
    fireEvent.click(screen.getByRole("button", { name: /Approve \(2\)/i }));

    await waitFor(() => {
      expect(setRating).toHaveBeenCalledWith("gallery-1", expect.objectContaining({ approved: true, flagged: false }));
      expect(setRating).toHaveBeenCalledWith("gallery-2", expect.objectContaining({ approved: true, flagged: false }));
    });
  });
});
