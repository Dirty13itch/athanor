import { MemoryConsole } from "@/features/memory/memory-console";
import { getMemorySnapshot } from "@/lib/subpage-data";

export const revalidate = 30;

export default async function PreferencesPage() {
  const snapshot = await getMemorySnapshot();
  return <MemoryConsole initialSnapshot={snapshot} variant="preferences" />;
}
