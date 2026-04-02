import { IdeasConsole } from "@/features/operator/ideas-console";

export const revalidate = 15;

export default async function IdeasPage() {
  return <IdeasConsole />;
}
