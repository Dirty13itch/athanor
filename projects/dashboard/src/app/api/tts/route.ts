import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";

// Proxy to Speaches TTS endpoint — avoids CORS for client components
// POST /api/tts with { input, voice?, speed? }
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { input, voice = "alloy", speed = 1.0 } = body;

    if (!input || typeof input !== "string") {
      return NextResponse.json({ error: "Missing input text" }, { status: 400 });
    }

    // Truncate to 4096 chars to prevent abuse
    const text = input.slice(0, 4096);

    if (isDashboardFixtureMode()) {
      return new NextResponse(Uint8Array.from([0x49, 0x44, 0x33]), {
        headers: {
          "Content-Type": "audio/mpeg",
          "Cache-Control": "private, max-age=3600",
          "X-Athanor-Fixture": "1",
          "X-Athanor-Voice": String(voice),
          "X-Athanor-Speed": String(speed),
          "X-Athanor-Text-Length": String(text.length),
        },
      });
    }

    const res = await fetch(`${config.speaches.url}/v1/audio/speech`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "tts-1",
        input: text,
        voice,
        speed,
        response_format: "mp3",
      }),
      signal: AbortSignal.timeout(30000),
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: `Speaches returned ${res.status}` },
        { status: res.status }
      );
    }

    // Stream the audio binary back to the client
    const audioData = await res.arrayBuffer();
    return new NextResponse(audioData, {
      headers: {
        "Content-Type": "audio/mpeg",
        "Cache-Control": "private, max-age=3600",
      },
    });
  } catch {
    return NextResponse.json({ error: "TTS service unreachable" }, { status: 502 });
  }
}
