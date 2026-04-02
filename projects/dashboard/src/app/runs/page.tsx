import { RunsConsole } from "@/features/operator/runs-console";

export const revalidate = 15;

export default async function RunsPage() {
  return <RunsConsole />;
}
