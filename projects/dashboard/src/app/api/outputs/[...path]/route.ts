import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const encodedPath = path.map(encodeURIComponent).join("/");
  return proxyAgentJson(`/v1/outputs/${encodedPath}`, undefined, "Failed to fetch output file");
}
