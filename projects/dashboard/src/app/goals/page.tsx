import { GoalsConsole } from "@/features/workforce/goals-console";
import { getWorkforceSnapshot } from "@/lib/dashboard-data";

export const revalidate = 15;

export default async function GoalsPage() {
  const snapshot = await getWorkforceSnapshot();
  return <GoalsConsole initialSnapshot={snapshot} />;
}
