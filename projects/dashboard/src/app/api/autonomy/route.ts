import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/autonomy", undefined, "Failed to fetch autonomy settings");
}
