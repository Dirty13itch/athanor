import { proxyAgentJson } from "@/lib/server-agent";

type Context = {
  params: Promise<{ programId: string }>;
};

export async function GET(_request: Request, context: Context) {
  const { programId } = await context.params;
  return proxyAgentJson(`/v1/bootstrap/programs/${programId}`, undefined, "Failed to fetch bootstrap program");
}
