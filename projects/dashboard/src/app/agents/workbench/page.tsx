import { AgentWorkbench } from "@/features/agents/agent-workbench";

export const revalidate = 15;

export default async function AgentWorkbenchPage() {
  return <AgentWorkbench />;
}
