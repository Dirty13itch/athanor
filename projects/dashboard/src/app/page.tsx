import { CommandCenter } from "@/features/overview/command-center";
import { getOverviewSnapshot } from "@/lib/dashboard-data";

export const revalidate = 30;

export default async function DashboardPage() {
  const snapshot = await getOverviewSnapshot();
  return <CommandCenter initialSnapshot={snapshot} />;
}
