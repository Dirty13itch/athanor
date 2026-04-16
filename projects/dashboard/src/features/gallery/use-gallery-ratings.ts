"use client";

import { useCallback, useEffect, useSyncExternalStore } from "react";
import type { GalleryRating, GalleryRatingsResponse } from "@/lib/contracts";
import { fetchGalleryRatings, persistGalleryRating } from "@/lib/gallery-ratings";

export type { GalleryRating } from "@/lib/contracts";

type Ratings = Record<string, GalleryRating>;

const EMPTY_RATINGS: Ratings = {};

let listeners: Array<() => void> = [];
let snapshotCache: Ratings = EMPTY_RATINGS;
let ratingsLoadPromise: Promise<void> | null = null;

function notify() {
  for (const listener of listeners) {
    listener();
  }
}

function applySnapshot(response: GalleryRatingsResponse) {
  snapshotCache = response.ratings;
  notify();
}

async function ensureRatingsLoaded() {
  if (!ratingsLoadPromise) {
    ratingsLoadPromise = fetchGalleryRatings()
      .then(applySnapshot)
      .catch(() => {
        snapshotCache = EMPTY_RATINGS;
      })
      .finally(() => {
        ratingsLoadPromise = null;
      });
  }

  return ratingsLoadPromise;
}

function subscribe(cb: () => void) {
  listeners = [...listeners, cb];
  return () => {
    listeners = listeners.filter((listener) => listener !== cb);
  };
}

function getSnapshot(): Ratings {
  return snapshotCache;
}

function getServerSnapshot(): Ratings {
  return EMPTY_RATINGS;
}

export function useGalleryRatings() {
  const ratings = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    void ensureRatingsLoaded();
  }, []);

  const getRating = useCallback((imageId: string): GalleryRating | undefined => ratings[imageId], [ratings]);

  const setRating = useCallback(async (imageId: string, rating: GalleryRating) => {
    const previous = snapshotCache;
    snapshotCache = { ...snapshotCache, [imageId]: rating };
    notify();

    try {
      const response = await persistGalleryRating({ imageId, rating });
      applySnapshot(response);
    } catch {
      snapshotCache = previous;
      notify();
    }
  }, []);

  return { ratings, getRating, setRating } as const;
}

export function __resetGalleryRatingsCacheForTests() {
  listeners = [];
  snapshotCache = EMPTY_RATINGS;
  ratingsLoadPromise = null;
}

export function __getGalleryRatingsServerSnapshotForTests() {
  return getServerSnapshot();
}
