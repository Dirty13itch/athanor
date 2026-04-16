import { AgentConsole } from "@/features/agents/agent-console";
import { getAgentsSnapshot } from "@/lib/dashboard-data";

export const revalidate = 30;

export default async function AgentsPage() {
  const agents = await getAgentsSnapshot();
  return <AgentConsole initialAgents={agents} />;
}
