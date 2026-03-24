import { WorkforceOverviewConsole } from "@/features/workforce/workforce-overview-console";
import { getWorkforceSnapshot } from "@/lib/dashboard-data";

export const revalidate = 15;

export default async function WorkforcePage() {
  const snapshot = await getWorkforceSnapshot();
  return <WorkforceOverviewConsole initialSnapshot={snapshot} />;
}
