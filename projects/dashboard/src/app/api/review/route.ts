import { getReviewSnapshot } from "@/lib/subpage-data";

export async function GET() {
  return Response.json(await getReviewSnapshot());
}
