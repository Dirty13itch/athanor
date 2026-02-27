import { config } from "@/lib/config";
import type { WorldState, DialogueTurn } from "@/types/game";

interface NarrateRequest {
  worldState: WorldState;
  recentHistory: DialogueTurn[];
  context?: string;
}

/**
 * Atmospheric narration API — generates environmental descriptions
 * for scenes without characters present. Shorter, moodier, more evocative
 * than dialogue generation.
 */
export async function POST(req: Request) {
  const body: NarrateRequest = await req.json();
  const { worldState, recentHistory, context } = body;

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
Content intensity: ${worldState.contentIntensity}/5.`;

  const messages = [
    { role: "system", content: systemPrompt },
    { role: "user", content: "Describe this moment." },
  ];

  const response = await fetch(`${config.litellmUrl}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.litellmKey}`,
    },
    body: JSON.stringify({
      model: config.dialogueModel,
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
