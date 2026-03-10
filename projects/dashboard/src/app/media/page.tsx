import { MediaConsole } from "@/features/media/media-console";
import { getMediaSnapshot } from "@/lib/subpage-data";

export const revalidate = 15;

export default async function MediaPage() {
  const snapshot = await getMediaSnapshot();
  return <MediaConsole initialSnapshot={snapshot} />;
}
