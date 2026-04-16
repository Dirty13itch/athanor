import { getMediaSnapshot } from "@/lib/subpage-data";

export async function GET() {
  return Response.json(await getMediaSnapshot());
}
