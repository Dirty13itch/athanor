import { HomeConsole } from "@/features/home/home-console";
import { getHomeSnapshot } from "@/lib/subpage-data";

export const revalidate = 30;

export default async function HomePage() {
  const snapshot = await getHomeSnapshot();
  return <HomeConsole initialSnapshot={snapshot} />;
}
