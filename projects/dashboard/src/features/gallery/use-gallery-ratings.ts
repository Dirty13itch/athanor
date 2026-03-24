"use client";

import { useCallback, useSyncExternalStore } from "react";

export interface GalleryRating {
  rating: number | null; // 1-5
  approved: boolean;
  flagged: boolean;
  notes: string;
  timestamp: string;
}

const STORAGE_KEY = "athanor-gallery-ratings";

type Ratings = Record<string, GalleryRating>;

// ---------------------------------------------------------------------------
// Tiny external-store wrapper around localStorage so all mounted components
// re-render when a rating changes (even across hooks).
// ---------------------------------------------------------------------------

let listeners: Array<() => void> = [];
let snapshotCache: Ratings | null = null;

function readStore(): Ratings {
  if (snapshotCache) return snapshotCache;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    snapshotCache = raw ? (JSON.parse(raw) as Ratings) : {};
  } catch {
    snapshotCache = {};
  }
  return snapshotCache;
}

function writeStore(next: Ratings) {
  snapshotCache = next;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  for (const fn of listeners) fn();
}

function subscribe(cb: () => void) {
  listeners = [...listeners, cb];
  return () => {
    listeners = listeners.filter((l) => l !== cb);
  };
}

function getSnapshot(): Ratings {
  return readStore();
}

function getServerSnapshot(): Ratings {
  return {};
}

// ---------------------------------------------------------------------------

export function useGalleryRatings() {
  const ratings = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const getRating = useCallback(
    (imageId: string): GalleryRating | undefined => ratings[imageId],
    [ratings],
  );

  const setRating = useCallback((imageId: string, rating: GalleryRating) => {
    const current = readStore();
    writeStore({ ...current, [imageId]: rating });
  }, []);

  return { ratings, getRating, setRating } as const;
}
