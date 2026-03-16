import { TopologyConsole } from "@/features/topology/topology-console";
import { config } from "@/lib/config";

export const revalidate = 15;

export default async function TopologyPage() {
  const nodes = config.nodes.map((n) => ({
    id: n.id,
    name: n.name,
    ip: n.ip,
    role: n.role,
  }));

  const models = config.inferenceBackends
    .filter((b) => b.id !== "litellm-proxy")
    .map((b) => ({
      nodeId: b.nodeId,
      name: b.primaryModel,
      alias: b.id,
      port: parseInt(new URL(b.url).port, 10),
      description: b.description,
    }));

  const nodeServices: Record<string, string[]> = {};
  for (const svc of config.services) {
    const nodeId = svc.nodeId;
    if (!nodeServices[nodeId]) nodeServices[nodeId] = [];
    nodeServices[nodeId].push(svc.name);
  }

  return (
    <TopologyConsole
      nodes={nodes}
      models={models}
      nodeServices={nodeServices}
    />
  );
}
