import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { __resetGalleryRatingsStoreForTests, saveGalleryRating } from "../store";
import { GET } from "./route";

describe("GET /api/gallery/ratings", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_GALLERY_RATINGS_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-gallery-ratings-"));
    env.DASHBOARD_GALLERY_RATINGS_PATH = path.join(tempDir, "gallery-ratings.json");
    await __resetGalleryRatingsStoreForTests();
  });

  afterEach(async () => {
    if (originalPath === undefined) {
      delete env.DASHBOARD_GALLERY_RATINGS_PATH;
    } else {
      env.DASHBOARD_GALLERY_RATINGS_PATH = originalPath;
    }

    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
      tempDir = "";
    }
  });

  it("returns stored ratings and supports status filtering", async () => {
    await saveGalleryRating("approved", {
      rating: 5,
      approved: true,
      flagged: false,
      notes: "",
      timestamp: "2026-03-25T12:00:00.000Z",
    });
    await saveGalleryRating("flagged", {
      rating: 1,
      approved: false,
      flagged: true,
      notes: "check",
      timestamp: "2026-03-25T12:00:00.000Z",
    });

    const response = await GET(new Request("http://localhost/api/gallery/ratings?filter=flagged"));
    expect(response.status).toBe(200);

    const payload = (await response.json()) as {
      source: string;
      filter: string;
      count: number;
      ratings: Record<string, unknown>;
    };

    expect(payload.source).toBe("file");
    expect(payload.filter).toBe("flagged");
    expect(payload.count).toBe(1);
    expect(Object.keys(payload.ratings)).toEqual(["flagged"]);
  });
});
