import { galleryRatingSchema } from "@/lib/contracts";
import { requireOperatorMutationAccess } from "@/lib/operator-auth";
import { saveGalleryRating } from "../store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * POST /api/gallery/rate - Persist a rating for an image.
 */
export async function POST(request: Request) {
  const gate = requireOperatorMutationAccess(request);
  if (gate) {
    return gate;
  }

  try {
    const body = await request.json().catch(() => ({}));
    const imageId = typeof body.imageId === "string" ? body.imageId.trim() : "";

    if (!imageId) {
      return Response.json({ error: "imageId is required" }, { status: 400 });
    }

    const ratingResult = galleryRatingSchema.safeParse({
      rating: body.rating ?? null,
      approved: body.approved,
      flagged: body.flagged,
      notes: typeof body.notes === "string" ? body.notes : "",
      timestamp: typeof body.timestamp === "string" ? body.timestamp : new Date().toISOString(),
    });

    if (!ratingResult.success) {
      return Response.json(
        { error: "Invalid rating payload", issues: ratingResult.error.flatten() },
        { status: 400 }
      );
    }

    const saved = await saveGalleryRating(imageId, ratingResult.data);
    return Response.json({
      ok: true,
      imageId,
      ...saved,
      rating: saved.ratings[imageId],
    });
  } catch (err) {
    return Response.json(
      { error: err instanceof Error ? err.message : "Failed to submit rating" },
      { status: 500 }
    );
  }
}
