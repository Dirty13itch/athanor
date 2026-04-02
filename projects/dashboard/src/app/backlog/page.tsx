import { BacklogConsole } from "@/features/operator/backlog-console";

export const revalidate = 15;

export default async function BacklogPage() {
  return <BacklogConsole />;
}
