import { config } from "@/lib/config";
import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";
import { QUEENS } from "@/data/queens";

/**
 * Voice generation API route — converts character dialogue to speech
 * using Speaches (OpenAI-compatible TTS API) on FOUNDRY:8200.
 *
 * POST /api/voice
 * Body: { characterId: string, text: string, speed?: number }
 * Returns: audio/mpeg stream
 */

/** Map queen archetypes to TTS voice presets */
const ARCHETYPE_VOICES: Record<string, string> = {
  ice: "nova",         // Cool, controlled
  warrior: "onyx",     // Strong, commanding
  seductress: "shimmer", // Warm, alluring
  innocent: "alloy",   // Light, youthful
  sorceress: "echo",   // Mysterious, resonant
  priestess: "fable",  // Warm, authoritative
  scholar: "nova",     // Clear, precise
  merchant: "onyx",    // Confident, direct
  defiant: "onyx",     // Fierce, powerful
  fire: "shimmer",     // Passionate, intense
  shadow: "echo",      // Quiet, cryptic
  sun: "alloy",        // Bright, charismatic
};

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  if (!body || typeof body.text !== "string" || !body.text.trim()) {
    return Response.json({ error: "text is required" }, { status: 400 });
  }

  const characterId = body.characterId as string | undefined;
  const text = body.text.trim();
  const speed = typeof body.speed === "number" ? Math.max(0.5, Math.min(2.0, body.speed)) : 1.0;

  if (EOQ_FIXTURE_MODE) {
    // Return a tiny silent MP3 for tests
    return new Response(new Uint8Array(0), {
      headers: { "Content-Type": "audio/mpeg" },
    });
  }

  // Determine voice from character archetype
  let voice = "nova";
  if (characterId) {
    const queen = QUEENS[characterId];
    if (queen) {
      voice = ARCHETYPE_VOICES[queen.archetype] ?? "nova";
    }
  }

  // Strip markdown formatting from text for cleaner speech
  const cleanText = text
    .replace(/\*([^*]+)\*/g, "$1")   // Remove italics markers
    .replace(/\*\*([^*]+)\*\*/g, "$1") // Remove bold markers
    .replace(/\[([^\]]+)\]/g, "$1")   // Remove bracket notation
    .trim();

  try {
    const response = await fetch(`${config.speachesUrl}/v1/audio/speech`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(30_000),
      body: JSON.stringify({
        model: "tts-1",
        input: cleanText.slice(0, 4096), // TTS API limit
        voice,
        speed,
        response_format: "mp3",
      }),
    });

    if (!response.ok) {
      const err = await response.text().catch(() => "unknown");
      console.error("Speaches TTS error:", response.status, err);
      return Response.json(
        { error: "TTS generation failed", detail: err },
        { status: 502 },
      );
    }

    // Stream the audio back to the client
    return new Response(response.body, {
      headers: {
        "Content-Type": "audio/mpeg",
        "Cache-Control": "public, max-age=3600",
      },
    });
  } catch (err) {
    console.error("Voice generation failed:", err);
    return Response.json(
      { error: "TTS service unavailable" },
      { status: 503 },
    );
  }
}
