import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: Request) {
  const search = new URL(request.url).searchParams.toString();
  return proxyAgentJson(`/v1/bootstrap/integrations${search ? `?${search}` : ""}`, undefined, "Failed to fetch bootstrap integrations");
}
