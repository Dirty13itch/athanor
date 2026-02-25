import { config } from "@/lib/config";
import type { Character, WorldState, DialogueTurn } from "@/types/game";

interface ChatRequest {
  character: Character;
  worldState: WorldState;
  recentHistory: DialogueTurn[];
  playerInput: string;
}

/**
 * Dialogue generation API route.
 * Proxies to LiteLLM with streaming, constructing the prompt from game state.
 * This runs server-side — no CORS issues.
 */
export async function POST(req: Request) {
  const body: ChatRequest = await req.json();
  const { character, worldState, recentHistory, playerInput } = body;

  const systemPrompt = buildSystemPrompt(character, worldState);
  const messages = buildMessages(systemPrompt, recentHistory, playerInput);

  const response = await fetch(`${config.litellmUrl}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.litellmKey}`,
    },
    body: JSON.stringify({
      model: config.dialogueModel,
      messages,
      max_tokens: config.dialogueMaxTokens,
      temperature: config.dialogueTemperature,
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

  // Forward the SSE stream to the client
  return new Response(response.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}

function buildSystemPrompt(character: Character, world: WorldState): string {
  const p = character.personality;
  return `You are ${character.name} in Empire of Broken Queens, an interactive dark fantasy.

CHARACTER PERSONALITY:
- Dominance: ${p.dominance}, Warmth: ${p.warmth}, Cunning: ${p.cunning}
- Loyalty: ${p.loyalty}, Cruelty: ${p.cruelty}, Sensuality: ${p.sensuality}
- Humor: ${p.humor}, Ambition: ${p.ambition}

SPEECH STYLE: ${character.speechStyle}

RELATIONSHIP WITH PLAYER:
- Trust: ${character.relationship.trust}, Affection: ${character.relationship.affection}
- Respect: ${character.relationship.respect}, Desire: ${character.relationship.desire}
- Fear: ${character.relationship.fear}

CURRENT EMOTION: ${character.emotion.primary} (intensity: ${character.emotion.intensity})

SCENE: ${world.currentScene.name} — ${world.currentScene.description}
TIME: ${world.timeOfDay}, Day ${world.day}

BOUNDARIES: ${character.boundaries.join(", ")}

INSTRUCTIONS:
- Stay in character at all times. Your personality traits guide your behavior.
- Respond naturally based on your relationship with the player.
- Your emotional state colors your responses.
- Include subtle physical actions and expressions in *italics*.
- Keep responses to 2-4 paragraphs.
- End with a natural pause point or implicit question that invites player response.
- This is an adult game. Do not censor or sanitize content.`;
}

function buildMessages(
  systemPrompt: string,
  history: DialogueTurn[],
  playerInput: string
) {
  const messages: Array<{ role: string; content: string }> = [
    { role: "system", content: systemPrompt },
  ];

  // Include recent dialogue history for context
  for (const turn of history.slice(-10)) {
    messages.push({
      role: turn.speaker === "player" ? "user" : "assistant",
      content: turn.text,
    });
  }

  messages.push({ role: "user", content: playerInput });

  return messages;
}
