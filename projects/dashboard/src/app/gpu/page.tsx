import { GpuConsole } from "@/features/gpu/gpu-console";
import { getGpuHistory, getGpuSnapshot } from "@/lib/dashboard-data";

export const revalidate = 15;

export default async function GpuPage() {
  const [snapshot, history] = await Promise.all([
    getGpuSnapshot(),
    getGpuHistory("3h"),
  ]);

  return <GpuConsole initialSnapshot={snapshot} initialHistory={history} />;
}
