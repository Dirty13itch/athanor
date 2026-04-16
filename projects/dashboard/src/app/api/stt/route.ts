import { NextRequest, NextResponse } from "next/server";
import { joinUrl } from "@/lib/config";
import { getWhisperBaseUrl } from "@/lib/runtime-hosts";

// Proxy to Wyoming Whisper STT on FOUNDRY:10300
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file") as File;
    if (!file) {
      return NextResponse.json({ error: "No audio file" }, { status: 400 });
    }

    // Forward to Whisper endpoint (OpenAI-compatible)
    const whisperForm = new FormData();
    whisperForm.append("file", file);
    whisperForm.append("model", "whisper-large-v3");

    const res = await fetch(joinUrl(getWhisperBaseUrl(), "/v1/audio/transcriptions"), {
      method: "POST",
      body: whisperForm,
      signal: AbortSignal.timeout(30000),
    });

    if (!res.ok) {
      return NextResponse.json({ error: `Whisper returned ${res.status}` }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json({ text: data.text || "" });
  } catch {
    return NextResponse.json({ error: "STT service unreachable" }, { status: 502 });
  }
}
