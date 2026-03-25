import { config } from "@/lib/config";
import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";
import { QUEENS } from "@/data/queens";

/**
 * Voice generation API route — converts character dialogue to speech
 * using Kokoro TTS via Speaches (OpenAI-compatible API) on FOUNDRY:8200.
 *
 * POST /api/voice
 * Body: { characterId: string, text: string, speed?: number }
 * Returns: audio/mpeg stream
 */

const KOKORO_MODEL = "speaches-ai/Kokoro-82M-v1.0-ONNX";

/**
 * Map queen archetypes to Kokoro voice presets.
 * Kokoro has 54 voices — prefixes: af_ (American female), bf_ (British female),
 * am_ (American male), bm_ (British male).
 *
 * Each archetype gets a voice that matches its personality:
 */
const ARCHETYPE_VOICES: Record<string, string> = {
  ice:        "bf_emma",    // Cold, commanding — British female, crisp
  warrior:    "af_nova",    // Fierce, powerful — American female, strong
  seductress: "af_bella",   // Warm, alluring — American female, warm
  innocent:   "af_sky",     // Light, youthful — American female, bright
  sorceress:  "bf_lily",    // Mysterious, resonant — British female, dark
  priestess:  "af_nicole",  // Warm, authoritative — American female, clear
  scholar:    "bf_emma",    // Clear, precise — British female, measured
  merchant:   "af_nicole",  // Confident, direct — American female
  defiant:    "af_nova",    // Fierce, powerful — American female, bold
  fire:       "af_bella",   // Passionate, intense — American female, warm
  shadow:     "bf_lily",    // Quiet, cryptic — British female, low
  sun:        "af_sky",     // Bright, charismatic — American female, upbeat
};

/** Narrator voice — distinguished male narrator */
const NARRATOR_VOICE = "bm_george";

/**
 * Per-character voice overrides. When a specific queen has a voice assigned
 * directly (e.g. via future UI), it takes priority over archetype mapping.
 */
const CHARACTER_VOICE_OVERRIDES: Record<string, string> = {
  // Examples — uncomment or add as voice-fitting sessions happen:
  // "emilie-ekstrom": "bf_emma",
  // "jordan-night": "af_bella",
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

  // Determine voice: per-character override > archetype mapping > narrator > default
  let voice = NARRATOR_VOICE;
  if (characterId === "narrator") {
    voice = NARRATOR_VOICE;
  } else if (characterId) {
    const override = CHARACTER_VOICE_OVERRIDES[characterId];
    if (override) {
      voice = override;
    } else {
      const queen = QUEENS[characterId];
      if (queen) {
        voice = ARCHETYPE_VOICES[queen.archetype] ?? "af_bella";
      }
    }
  }

  // Strip markdown formatting from text for cleaner speech
  const cleanText = text
    .replace(/\*\*([^*]+)\*\*/g, "$1") // Remove bold markers (check first — greedy)
    .replace(/\*([^*]+)\*/g, "$1")     // Remove italics markers
    .replace(/\[([^\]]+)\]/g, "$1")    // Remove bracket notation
    .trim();

  try {
    const response = await fetch(`${config.speachesUrl}/v1/audio/speech`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(30_000),
      body: JSON.stringify({
        model: KOKORO_MODEL,
        input: cleanText.slice(0, 4096), // TTS API limit
        voice,
        speed,
        response_format: "mp3",
      }),
    });

    if (!response.ok) {
      const err = await response.text().catch(() => "unknown");
      console.error("Kokoro TTS error:", response.status, err);
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
