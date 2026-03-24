import { RoutingConsole } from "@/features/routing/routing-console";

export const revalidate = 15;

export default async function RoutingPage() {
  return <RoutingConsole />;
}
