import { MonitoringConsole } from "@/features/monitoring/monitoring-console";
import { getMonitoringSnapshot } from "@/lib/subpage-data";

export const dynamic = "force-dynamic";

export default async function MonitoringPage() {
  const snapshot = await getMonitoringSnapshot();
  return <MonitoringConsole initialSnapshot={snapshot} />;
}
