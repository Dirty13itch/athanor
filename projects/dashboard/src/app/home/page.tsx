import { HomeConsole } from "@/features/home/home-console";
import { getHomeSnapshot } from "@/lib/subpage-data";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const snapshot = await getHomeSnapshot();
  return <HomeConsole initialSnapshot={snapshot} />;
}
