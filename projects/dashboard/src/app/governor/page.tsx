import { GovernorConsole } from "@/features/governor/governor-console";

export const revalidate = 15;

export default async function GovernorPage() {
  return <GovernorConsole />;
}
