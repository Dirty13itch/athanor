import { NotificationsConsole } from "@/features/workforce/notifications-console";
import { getWorkforceSnapshot } from "@/lib/dashboard-data";

export const revalidate = 15;

export default async function NotificationsPage() {
  const snapshot = await getWorkforceSnapshot();
  return <NotificationsConsole initialSnapshot={snapshot} />;
}
