import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  __resetGalleryRatingsStoreForTests,
  readGalleryRatings,
  saveGalleryRating,
} from "./store";

describe("gallery ratings store", () => {
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

  it("persists ratings to disk and reloads them", async () => {
    const rating = {
      rating: 5,
      approved: true,
      flagged: false,
      notes: "keep",
      timestamp: "2026-03-25T12:00:00.000Z",
    };

    await saveGalleryRating("image-1", rating);
    const snapshot = await readGalleryRatings();

    expect(snapshot.source).toBe("file");
    expect(snapshot.count).toBe(1);
    expect(snapshot.ratings["image-1"]).toMatchObject(rating);
  });

  it("filters persisted ratings by status", async () => {
    await saveGalleryRating("approved", {
      rating: 5,
      approved: true,
      flagged: false,
      notes: "",
      timestamp: "2026-03-25T12:00:00.000Z",
    });
    await saveGalleryRating("rejected", {
      rating: 2,
      approved: false,
      flagged: false,
      notes: "not quite there",
      timestamp: "2026-03-25T12:00:00.000Z",
    });

    const approved = await readGalleryRatings("approved");
    const rejected = await readGalleryRatings("rejected");
    const unrated = await readGalleryRatings("unrated");

    expect(Object.keys(approved.ratings)).toEqual(["approved"]);
    expect(Object.keys(rejected.ratings)).toEqual(["rejected"]);
    expect(Object.keys(unrated.ratings)).toEqual([]);
  });
});
