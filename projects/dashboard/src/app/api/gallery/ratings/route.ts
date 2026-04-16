import { readGalleryRatings } from "../store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * GET /api/gallery/ratings - Fetch persisted ratings.
 * Optional query: ?filter=all|approved|flagged|rejected|unrated
 */
export async function GET(request: Request) {
  const filter = new URL(request.url).searchParams.get("filter");
  const snapshot = await readGalleryRatings(filter);

  return Response.json(snapshot);
}
