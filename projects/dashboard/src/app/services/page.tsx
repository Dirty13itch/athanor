import { ServicesConsole } from "@/features/services/services-console";
import { getServicesHistory, getServicesSnapshot } from "@/lib/dashboard-data";

export const revalidate = 15;

export default async function ServicesPage() {
  const [snapshot, history] = await Promise.all([
    getServicesSnapshot(),
    getServicesHistory("3h"),
  ]);

  return <ServicesConsole initialSnapshot={snapshot} initialHistory={history} />;
}
