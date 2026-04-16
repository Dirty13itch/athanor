import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  __getGalleryRatingsServerSnapshotForTests,
  __resetGalleryRatingsCacheForTests,
  useGalleryRatings,
} from "./use-gallery-ratings";

describe("useGalleryRatings", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    __resetGalleryRatingsCacheForTests();
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads persisted ratings and saves updates through the API", async () => {
    const initialRatings = {
      "image-1": {
        rating: 4,
        approved: true,
        flagged: false,
        notes: "loaded",
        timestamp: "2026-03-25T12:00:00.000Z",
      },
    };

    fetchMock.mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/api/gallery/ratings") && (!init || init.method === undefined || init.method === "GET")) {
        return Response.json({
          source: "file",
          filter: "all",
          updatedAt: "2026-03-25T12:00:00.000Z",
          count: 1,
          ratings: initialRatings,
        });
      }

      if (url.endsWith("/api/gallery/rate") && init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as {
          imageId: string;
          rating: typeof initialRatings["image-1"];
        };
        const nextRatings = {
          ...initialRatings,
          [body.imageId]: body.rating,
        };
        return Response.json({
          source: "file",
          filter: "all",
          updatedAt: "2026-03-25T12:01:00.000Z",
          count: Object.keys(nextRatings).length,
          ratings: nextRatings,
        });
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });

    const { result } = renderHook(() => useGalleryRatings());

    await waitFor(() => {
      expect(result.current.getRating("image-1")).toMatchObject({ rating: 4, approved: true, notes: "loaded" });
    });

    await act(async () => {
      await result.current.setRating("image-2", {
        rating: 5,
        approved: false,
        flagged: false,
        notes: "saved",
        timestamp: "2026-03-25T12:02:00.000Z",
      });
    });

    await waitFor(() => {
      expect(result.current.getRating("image-2")).toMatchObject({ rating: 5, notes: "saved" });
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/ratings",
      expect.objectContaining({ cache: "no-store" })
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/rate",
      expect.objectContaining({
        method: "POST",
      })
    );
  });

  it("keeps the server snapshot referentially stable when no ratings are loaded", () => {
    const first = __getGalleryRatingsServerSnapshotForTests();
    const second = __getGalleryRatingsServerSnapshotForTests();

    expect(first).toBe(second);
    expect(first).toEqual({});
  });
});
