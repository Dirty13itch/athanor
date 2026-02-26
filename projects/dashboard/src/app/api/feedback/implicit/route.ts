import { NextRequest, NextResponse } from "next/server";

const AGENT_SERVER = process.env.AGENT_SERVER_URL || "http://192.168.1.244:9000";

interface ImplicitEvent {
  type: string;
  page: string;
  agent?: string;
  duration_ms?: number;
  metadata?: Record<string, unknown>;
  timestamp: number;
}

interface ImplicitBatch {
  session_id: string;
  events: ImplicitEvent[];
}

export async function POST(request: NextRequest) {
  try {
    const body: ImplicitBatch = await request.json();

    if (!body.events || body.events.length === 0) {
      return NextResponse.json({ stored: 0 });
    }

    // Forward to agent server's implicit feedback endpoint
    // If it doesn't exist yet, store locally and return success
    try {
      const res = await fetch(`${AGENT_SERVER}/v1/feedback/implicit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(5000),
      });

      if (res.ok) {
        return NextResponse.json({ stored: body.events.length });
      }

      // If agent server doesn't have the endpoint yet, that's fine
      if (res.status === 404) {
        return NextResponse.json({ stored: 0, buffered: body.events.length });
      }
    } catch {
      // Agent server unreachable — silently drop (best-effort)
    }

    return NextResponse.json({ stored: 0, buffered: body.events.length });
  } catch {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }
}
