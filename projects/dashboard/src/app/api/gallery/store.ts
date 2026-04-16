import { randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import type { GalleryRating, GalleryRatingsResponse } from "@/lib/contracts";

interface GalleryRatingsFile {
  version: 1;
  updatedAt: string;
  ratings: Record<string, GalleryRating>;
}

const STORE_FILENAME = "gallery-ratings.json";
const DEFAULT_STORE_PATH = path.join(process.cwd(), ".data", STORE_FILENAME);

let writeQueue: Promise<void> = Promise.resolve();

function nowIso(): string {
  return new Date().toISOString();
}

function resolveStorePath(): string {
  return process.env.DASHBOARD_GALLERY_RATINGS_PATH?.trim() || DEFAULT_STORE_PATH;
}

function defaultStore(): GalleryRatingsFile {
  return {
    version: 1,
    updatedAt: nowIso(),
    ratings: {},
  };
}

async function readStoreFile(): Promise<GalleryRatingsFile> {
  const storePath = resolveStorePath();
  try {
    const raw = await readFile(storePath, "utf8");
    const parsed = JSON.parse(raw) as Partial<GalleryRatingsFile>;
    if (!parsed || typeof parsed !== "object" || !parsed.ratings || typeof parsed.ratings !== "object") {
      return defaultStore();
    }
    return {
      version: 1,
      updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : nowIso(),
      ratings: parsed.ratings as Record<string, GalleryRating>,
    };
  } catch {
    return defaultStore();
  }
}

async function writeStoreFile(store: GalleryRatingsFile): Promise<void> {
  const storePath = resolveStorePath();
  await mkdir(path.dirname(storePath), { recursive: true });

  const tempPath = `${storePath}.${randomUUID()}.tmp`;
  await writeFile(tempPath, `${JSON.stringify(store, null, 2)}\n`, "utf8");
  await rename(tempPath, storePath);
}

function normalizeRating(rating: GalleryRating): GalleryRating {
  return {
    rating: rating.rating === null ? null : Math.max(0, Math.min(5, Math.trunc(rating.rating))),
    approved: Boolean(rating.approved),
    flagged: Boolean(rating.flagged),
    notes: rating.notes ?? "",
    timestamp: rating.timestamp || nowIso(),
  };
}

function filterRatings(
  ratings: Record<string, GalleryRating>,
  filter: string | null
): Record<string, GalleryRating> {
  const normalizedFilter = (filter?.trim() || "all").toLowerCase();
  if (normalizedFilter === "all") {
    return ratings;
  }

  const entries = Object.entries(ratings).filter(([, rating]) => {
    if (normalizedFilter === "approved") {
      return rating.approved;
    }
    if (normalizedFilter === "flagged") {
      return rating.flagged;
    }
    if (normalizedFilter === "rejected") {
      return !rating.approved && !rating.flagged && rating.rating !== null;
    }
    if (normalizedFilter === "unrated") {
      return !rating.approved && !rating.flagged && rating.rating === null;
    }
    return true;
  });

  return Object.fromEntries(entries);
}

function toResponse(store: GalleryRatingsFile, filter: string | null): GalleryRatingsResponse {
  const effectiveFilter = filter?.trim() || "all";
  const ratings = filterRatings(store.ratings, effectiveFilter);
  return {
    source: "file",
    filter: effectiveFilter,
    updatedAt: store.updatedAt,
    count: Object.keys(ratings).length,
    ratings,
  };
}

async function mutateStore(
  updater: (store: GalleryRatingsFile) => GalleryRatingsFile
): Promise<GalleryRatingsResponse> {
  const next = writeQueue.then(async () => {
    const current = await readStoreFile();
    const updated = updater(current);
    updated.updatedAt = nowIso();
    await writeStoreFile(updated);
    return updated;
  });

  writeQueue = next.then(() => undefined, () => undefined);
  const store = await next;
  return toResponse(store, null);
}

export async function readGalleryRatings(filter: string | null = null): Promise<GalleryRatingsResponse> {
  const store = await readStoreFile();
  return toResponse(store, filter);
}

export async function saveGalleryRating(imageId: string, rating: GalleryRating): Promise<GalleryRatingsResponse> {
  const normalized = normalizeRating(rating);
  return mutateStore((store) => ({
    ...store,
    ratings: {
      ...store.ratings,
      [imageId]: normalized,
    },
  }));
}

export async function __resetGalleryRatingsStoreForTests(): Promise<void> {
  writeQueue = Promise.resolve();
}
