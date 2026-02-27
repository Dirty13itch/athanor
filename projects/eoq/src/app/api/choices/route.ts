import { config } from "@/lib/config";
import { getBreakingStage } from "@/types/game";
import type { Character, WorldState, DialogueTurn, PlayerChoice, BreakingMethod } from "@/types/game";

interface ChoicesRequest {
  character: Character;
  worldState: WorldState;
  recentHistory: DialogueTurn[];
}

/**
 * Generates contextual player choices based on the current game state.
 * Uses a non-streaming call to the LLM with structured output instructions.
 */
export async function POST(req: Request) {
  const body: ChoicesRequest = await req.json();
  const { character, worldState, recentHistory } = body;

  const stage = getBreakingStage(character.resistance);
  const rel = character.relationship;

  const systemPrompt = `You are a game master for Empire of Broken Queens, an adult dark fantasy interactive fiction game.

Generate 3-4 player dialogue choices for the current situation. Each choice should:
- Feel natural to the conversation
- Represent different approaches (diplomatic, aggressive, seductive, cunning, etc.)
- Include at least one option that could lower the character's resistance (breaking path)
- Include at least one option that builds genuine trust/respect (relationship path)

CURRENT CHARACTER: ${character.name} (${character.archetype})
- Resistance: ${character.resistance}/100 (stage: ${stage})
- Trust: ${rel.trust}, Respect: ${rel.respect}, Affection: ${rel.affection}
- Desire: ${rel.desire}, Fear: ${rel.fear}
- Emotional state: fear ${character.emotionalProfile.fear}, defiance ${character.emotionalProfile.defiance}, arousal ${character.emotionalProfile.arousal}, submission ${character.emotionalProfile.submission}, despair ${character.emotionalProfile.despair}
- Most vulnerable to: ${getVulnerabilities(character)}
- Boundaries: ${character.boundaries.slice(0, 2).join(". ")}
- Content intensity: ${worldState.contentIntensity}/5

SCENE: ${worldState.currentScene.name}

Respond with ONLY a JSON array. Each element has:
- "text": the player's dialogue (1-2 sentences, in character as the player)
- "intent": brief description of what this signals (e.g., "intimidation", "genuine_concern", "manipulation")
- "breaking_method": one of "physical", "psychological", "magical", "social" or null if not a breaking action
- "effects": object with numeric deltas: trust, affection, respect, desire, fear, resistance, corruption
  - Relationship values range from -15 to +15 per choice
  - Resistance changes range from -10 to +5 (negative = weaken their resistance)
  - Only include non-zero values

Example format:
[
  {"text": "Your people need a strong leader, not a prisoner.", "intent": "appeal_to_duty", "breaking_method": null, "effects": {"trust": 5, "respect": 8}},
  {"text": "You look cold. Allow me to warm you.", "intent": "seduction", "breaking_method": "social", "effects": {"desire": 10, "resistance": -5, "arousal": 5}}
]`;

  const messages: Array<{ role: string; content: string }> = [
    { role: "system", content: systemPrompt },
  ];

  // Include the last few turns of dialogue for context
  for (const turn of recentHistory.slice(-6)) {
    const charName = turn.speaker === "player" ? "Player" :
      turn.speaker === "narrator" ? "Narrator" : character.name;
    messages.push({
      role: "user",
      content: `[${charName}]: ${turn.text}`,
    });
  }

  messages.push({
    role: "user",
    content: "Generate player choices for this moment. Respond ONLY with a JSON array.",
  });

  try {
    const response = await fetch(`${config.litellmUrl}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.litellmKey}`,
      },
      body: JSON.stringify({
        model: config.dialogueModel,
        messages,
        max_tokens: 600,
        temperature: 0.9,
        stream: false,
      }),
    });

    if (!response.ok) {
      return Response.json({ choices: [] }, { status: 200 });
    }

    const data = await response.json();
    let content = data.choices?.[0]?.message?.content ?? "";

    // Strip think blocks and extract JSON
    content = content.replace(/<think>[\s\S]*?<\/think>/g, "").trim();

    // Find JSON array in the response
    const jsonMatch = content.match(/\[[\s\S]*\]/);
    if (!jsonMatch) {
      return Response.json({ choices: [] });
    }

    const rawChoices = JSON.parse(jsonMatch[0]);
    const choices: PlayerChoice[] = rawChoices.map((c: {
      text: string;
      intent: string;
      breaking_method?: string | null;
      effects?: Record<string, number>;
    }) => {
      const effects: Record<string, unknown> = {};
      if (c.effects) {
        // Map flat effect keys to our ChoiceEffects structure
        for (const [key, val] of Object.entries(c.effects)) {
          if (key === "arousal" || key === "submission" || key === "fear_emotion" || key === "defiance" || key === "despair") {
            // These go into emotionalShifts
            if (!effects.emotionalShifts) effects.emotionalShifts = {};
            (effects.emotionalShifts as Record<string, number>)[key === "fear_emotion" ? "fear" : key] = val;
          } else {
            effects[key] = val;
          }
        }
      }
      return {
        text: c.text,
        intent: c.intent,
        breakingMethod: (c.breaking_method as BreakingMethod) ?? undefined,
        effects: Object.keys(effects).length > 0 ? effects : undefined,
      };
    });

    return Response.json({ choices });
  } catch (err) {
    console.error("Choice generation failed:", err);
    return Response.json({ choices: [] });
  }
}

function getVulnerabilities(character: Character): string {
  const vulns = Object.entries(character.vulnerabilities)
    .filter(([, v]) => v != null && v > 0)
    .sort(([, a], [, b]) => (b ?? 0) - (a ?? 0))
    .map(([method, score]) => `${method} (${score})`)
    .join(", ");
  return vulns || "none identified";
}
