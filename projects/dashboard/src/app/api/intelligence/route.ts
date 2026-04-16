import { getIntelligenceSnapshot } from "@/lib/subpage-data";

export async function GET() {
  return Response.json(await getIntelligenceSnapshot());
}
