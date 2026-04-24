import { ReviewConsole } from "@/features/review/review-console";
import { getReviewSnapshot } from "@/lib/subpage-data";

export const revalidate = 15;

export default async function ReviewPage() {
  const snapshot = await getReviewSnapshot();
  return <ReviewConsole initialSnapshot={snapshot} />;
}
