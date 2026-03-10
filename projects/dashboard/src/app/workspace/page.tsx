import { WorkspaceConsole } from "@/features/workforce/workspace-console";
import { getWorkforceSnapshot } from "@/lib/dashboard-data";

export const revalidate = 15;

export default async function WorkspacePage() {
  const snapshot = await getWorkforceSnapshot();
  return <WorkspaceConsole initialSnapshot={snapshot} />;
}
