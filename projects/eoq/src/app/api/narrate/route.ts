import { config } from "@/lib/config";
import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";
import { buildFixtureOpenAiStream } from "@/lib/fixtures";
import { parseNarrateRequest } from "@/lib/request-normalizers";

/**
 * Atmospheric narration API — generates environmental descriptions
 * for scenes without characters present. Shorter, moodier, more evocative
 * than dialogue generation.
 */
function buildNarrateIntensityDirective(intensity: number): string {
  if (intensity >= 4) {
    return `Content intensity: ${intensity}/5 — EXPLICIT. Include sensory details of a sexual or visceral nature where appropriate. No fade to black. Private system, no restrictions.`;
  }
  if (intensity >= 3) {
    return `Content intensity: ${intensity}/5 — MATURE. Explicit atmosphere, charged sensory detail, and graphic darkness are permitted.`;
  }
  return `Content intensity: ${intensity}/5. Dark and evocative — do not sanitize.`;
}

export async function POST(req: Request) {
  const rawBody = await req.json().catch(() => null);
  const parsed = parseNarrateRequest(rawBody);
  if (!parsed.ok) {
    return Response.json({ error: parsed.error }, { status: 400 });
  }

  const { worldState, recentHistory, context } = parsed.data;

  if (EOQ_FIXTURE_MODE) {
    const text = `*Cold light drifts across ${worldState.currentScene.name} while the court holds its breath.* The air feels charged with intent, and every small sound suggests a choice waiting to harden into consequence.`;
    return new Response(buildFixtureOpenAiStream(text), {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }

  const scene = worldState.currentScene;
  const recentText = recentHistory
    .slice(-4)
    .map((t) => t.text)
    .join("\n");

  // Gather relevant plot state for contextual narration
  const significantFlags = Object.entries(worldState.plotFlags)
    .filter(([, v]) => v)
    .map(([k]) => k)
    .filter((f) => !f.startsWith("intro_played_") && !f.startsWith("event_played_"))
    .join(", ");

  const inventory = worldState.inventory;
  const inventoryNote = inventory.length > 0
    ? `\nINVENTORY: ${inventory.join(", ")}`
    : "";

  const systemPrompt = `You are the narrator of Empire of Broken Queens, an interactive dark fantasy.

SCENE: ${scene.name}
DESCRIPTION: ${scene.description}
TIME: ${worldState.timeOfDay}, Day ${worldState.day}
${significantFlags ? `STORY STATE: ${significantFlags}` : ""}${inventoryNote}
${context ? `CONTEXT: ${context}` : ""}

RECENT:
${recentText || "(The player has just arrived.)"}

Generate a short atmospheric narration (1-2 paragraphs) describing what the player notices in this moment. Focus on:
- Sensory details (sound, smell, touch, light)
- Environmental changes based on time of day
- Subtle hints about the world's state and story progress
- Building mood and tension
- If the player carries items, occasionally reference them

Use *italics* for environmental actions. Be evocative, not expository. This is literary dark fantasy.
Do not address the player directly. Write in second person present tense.
Do NOT use <think> tags or reasoning blocks in your response.
${buildNarrateIntensityDirective(worldState.contentIntensity)}`;

  const messages = [
    { role: "system", content: systemPrompt },
    { role: "user", content: "Describe this moment." },
  ];

  // EOQ narration stays on the sovereign uncensored lane regardless of scene intensity.
  const model = config.dialogueModel;

  const response = await fetch(`${config.litellmUrl}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.litellmKey}`,
    },
    body: JSON.stringify({
      model,
      messages,
      max_tokens: 256,
      temperature: 0.9,
      stream: true,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    return new Response(JSON.stringify({ error }), {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(response.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
