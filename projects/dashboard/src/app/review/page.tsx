import { IntelligenceConsole } from "@/features/intelligence/intelligence-console";
import { getIntelligenceSnapshot } from "@/lib/subpage-data";

export const revalidate = 15;

export default async function ReviewPage() {
  const snapshot = await getIntelligenceSnapshot();
  return <IntelligenceConsole initialSnapshot={snapshot} variant="review" />;
}
