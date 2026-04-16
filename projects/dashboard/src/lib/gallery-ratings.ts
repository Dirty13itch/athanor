import { galleryRatingsResponseSchema, type GalleryRating, type GalleryRatingsResponse } from "@/lib/contracts";
import { fetchJson } from "@/lib/http";

export type { GalleryRating } from "@/lib/contracts";

export interface GalleryRatingRequest {
  imageId: string;
  rating: GalleryRating;
}

export async function fetchGalleryRatings(filter?: string): Promise<GalleryRatingsResponse> {
  const query = filter ? `?filter=${encodeURIComponent(filter)}` : "";
  return fetchJson(`/api/gallery/ratings${query}`, { cache: "no-store" }, galleryRatingsResponseSchema);
}

export async function persistGalleryRating(request: GalleryRatingRequest): Promise<GalleryRatingsResponse> {
  return fetchJson(
    "/api/gallery/rate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      cache: "no-store",
    },
    galleryRatingsResponseSchema
  );
}
