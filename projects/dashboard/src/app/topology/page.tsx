import { TopologyConsole } from "@/features/topology/topology-console";

export const revalidate = 15;

export default async function TopologyPage() {
  return <TopologyConsole />;
}
