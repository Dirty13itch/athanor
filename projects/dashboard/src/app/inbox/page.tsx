import { InboxConsole } from "@/features/operator/inbox-console";

export const revalidate = 15;

export default async function InboxPage() {
  return <InboxConsole />;
}
