import { WorkPlannerConsole } from "@/features/workforce/work-planner-console";
import { getWorkforceSnapshot } from "@/lib/dashboard-data";

export const revalidate = 15;

export default async function WorkPlannerPage() {
  const snapshot = await getWorkforceSnapshot();
  return <WorkPlannerConsole initialSnapshot={snapshot} />;
}
