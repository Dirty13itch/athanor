import { NextResponse } from "next/server";
import { config } from "@/lib/config";

export interface AgentInfo {
  name: string;
  description: string;
  tools: string[];
  type: string;
  schedule?: string;
  status: "online" | "planned";
  status_note?: string;
}

export async function GET() {
  try {
    const res = await fetch(`${config.agentServer.url}/v1/agents`, {
      signal: AbortSignal.timeout(5000),
    });

    if (!res.ok) {
      return NextResponse.json({ status: "offline", agents: [] });
    }

    const data = await res.json();
    return NextResponse.json({ status: "online", agents: data.agents ?? [] });
  } catch {
    return NextResponse.json({ status: "offline", agents: [] });
  }
}
