import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { __resetGalleryRatingsStoreForTests } from "../store";
import { POST } from "./route";

describe("POST /api/gallery/rate", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_GALLERY_RATINGS_PATH;
  const originalToken = env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-gallery-ratings-"));
    env.DASHBOARD_GALLERY_RATINGS_PATH = path.join(tempDir, "gallery-ratings.json");
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "secret-token";
    await __resetGalleryRatingsStoreForTests();
  });

  afterEach(async () => {
    if (originalPath === undefined) {
      delete env.DASHBOARD_GALLERY_RATINGS_PATH;
    } else {
      env.DASHBOARD_GALLERY_RATINGS_PATH = originalPath;
    }

    if (originalToken === undefined) {
      delete env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
    } else {
      env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = originalToken;
    }

    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
      tempDir = "";
    }
  });

  it("rejects unauthenticated requests", async () => {
    const response = await POST(
      new Request("http://localhost/api/gallery/rate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          imageId: "image-denied",
          rating: 4,
          approved: true,
          flagged: false,
          notes: "blocked",
        }),
      })
    );

    expect(response.status).toBe(403);
  });

  it("persists a rating and returns the updated snapshot", async () => {
    const response = await POST(
      new Request("http://localhost/api/gallery/rate", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          cookie: "athanor_operator_session=secret-token",
          origin: "http://localhost",
        },
        body: JSON.stringify({
          imageId: "image-1",
          rating: 4,
          approved: true,
          flagged: false,
          notes: "persisted",
        }),
      })
    );

    expect(response.status).toBe(200);

    const payload = (await response.json()) as {
      ok: boolean;
      imageId: string;
      ratings: Record<string, unknown>;
      rating: Record<string, unknown>;
    };

    expect(payload.ok).toBe(true);
    expect(payload.imageId).toBe("image-1");
    expect(payload.rating).toMatchObject({ rating: 4, approved: true, flagged: false, notes: "persisted" });
    expect(payload.ratings["image-1"]).toMatchObject({ rating: 4, approved: true, flagged: false });
  });

  it("rejects invalid payloads", async () => {
    const response = await POST(
      new Request("http://localhost/api/gallery/rate", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          cookie: "athanor_operator_session=secret-token",
          origin: "http://localhost",
        },
        body: JSON.stringify({
          imageId: "",
          rating: 8,
          approved: true,
          flagged: false,
          notes: "",
        }),
      })
    );

    expect(response.status).toBe(400);
  });
});
