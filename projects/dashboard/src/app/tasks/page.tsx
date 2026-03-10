import { TasksConsole } from "@/features/workforce/tasks-console";
import { getWorkforceSnapshot } from "@/lib/dashboard-data";

export const revalidate = 15;

export default async function TasksPage() {
  const snapshot = await getWorkforceSnapshot();
  return <TasksConsole initialSnapshot={snapshot} />;
}
