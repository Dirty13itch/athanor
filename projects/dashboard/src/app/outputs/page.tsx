import { HistoryConsole } from "@/features/history/history-console";
import { getHistorySnapshot } from "@/lib/subpage-data";

export const revalidate = 15;

export default async function OutputsPage() {
  const snapshot = await getHistorySnapshot();
  return <HistoryConsole initialSnapshot={snapshot} variant="outputs" />;
}
