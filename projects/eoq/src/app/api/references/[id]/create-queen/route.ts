import { readFile, writeFile } from "fs/promises";
import { join } from "path";
import { config } from "@/lib/config";
import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";

const REFERENCES_DIR = process.env.REFERENCES_DIR ?? "/references";
const METADATA_FILE = join(REFERENCES_DIR, "personas.json");

interface PersonaEntry {
  id: string;
  name: string;
  category: string;
  folder: string;
  photos: string[];
  createdAt: string;
  queenProfile?: unknown;
}

async function loadPersonas(): Promise<PersonaEntry[]> {
  try {
    const raw = await readFile(METADATA_FILE, "utf-8");
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

async function savePersonas(personas: PersonaEntry[]): Promise<void> {
  await writeFile(METADATA_FILE, JSON.stringify(personas, null, 2));
}

const QUEEN_GENERATION_PROMPT = `You are a game designer creating character profiles for "Empire of Broken Queens," a dark fantasy interactive narrative.

Given a persona name, generate a complete Queen profile as a JSON object. The queen should feel unique, with internally consistent personality and DNA traits.

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{
  "name": "<full name>",
  "title": "<short evocative title like 'The Ice Heiress' or 'The Shadow Dancer'>",
  "archetype": "<one of: ice, seductress, shadow, warrior, sorceress, scholar>",
  "resistance": <60-95>,
  "corruption": <0-20>,
  "vulnerabilities": {
    "physical": <-1.0 to 1.0>,
    "psychological": <-1.0 to 1.0>,
    "magical": <-1.0 to 1.0>,
    "social": <-1.0 to 1.0>
  },
  "personality": {
    "dominance": <0-1>, "warmth": <0-1>, "cunning": <0-1>,
    "loyalty": <0-1>, "cruelty": <0-1>, "sensuality": <0-1>,
    "humor": <0-1>, "ambition": <0-1>
  },
  "speechStyle": "<2-3 sentences describing how she talks>",
  "boundaries": ["<boundary 1>", "<boundary 2>", "<boundary 3>", "<boundary 4>"],
  "sexualDNA": {
    "desireType": "<responsive|spontaneous|hybrid>",
    "accelBrake": "<description of arousal pattern>",
    "painTolerance": <1-10>,
    "humiliationEnjoyment": <1-10>,
    "exhibitionismLevel": <1-10>,
    "gaggingResponse": "<fights|pushes-through|enjoys|breaks|minimal|legendary-pusher>",
    "moaningStyle": "<description>",
    "tearTrigger": "<what makes her cry>",
    "orgasmStyle": "<description>",
    "awakeningType": "<always-knew|total-surprise|slow-realization|denial-until-forced>",
    "blackmailNeed": "<none|necessary|heightens-it|bored-without-it|begs-for-it>",
    "addictionSpeed": "<very-slow|slow-burn|normal|fast|instant>",
    "jealousyType": "<possessive|competitive|turns-her-on|doesnt-care|none>",
    "aftercareNeed": "<none|light|medium|heavy>",
    "switchPotential": <1-10>,
    "groupSexAttitude": "<hates|tolerates|curious|craves|initiates>",
    "roleplayAffinity": "<description of what she likes>",
    "betrayalThreshold": <1-10>,
    "voiceDNA": "<how she sounds during sex>"
  },
  "stripperArc": {
    "club": "<club name>",
    "stageName": "<her stage name>",
    "quitReason": "<why she quit>",
    "returnTrigger": "<what pulls her back>",
    "uniqueKink": "<her signature thing>"
  },
  "awakening": "<1-2 sentences about her sexual awakening arc>",
  "performerReference": "<the persona name>"
}`;

/**
 * POST /api/references/[id]/create-queen
 * Generate a queen profile for a persona using the LLM.
 * Optionally accepts { customPrompt: string } for extra guidance.
 */
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  if (EOQ_FIXTURE_MODE) {
    return Response.json({ error: "Not available in fixture mode" }, { status: 400 });
  }

  const personas = await loadPersonas();
  const personaIdx = personas.findIndex((p) => p.id === id);
  if (personaIdx === -1) {
    return Response.json({ error: "Persona not found" }, { status: 404 });
  }

  const persona = personas[personaIdx];
  const body = await req.json().catch(() => ({})) as { customPrompt?: string };

  const userPrompt = `Create a queen profile for: "${persona.name}"${
    body.customPrompt ? `\n\nAdditional guidance: ${body.customPrompt}` : ""
  }`;

  const response = await fetch(`${config.litellmUrl}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.litellmKey}`,
    },
    body: JSON.stringify({
      model: "reasoning",
      messages: [
        { role: "system", content: QUEEN_GENERATION_PROMPT },
        { role: "user", content: userPrompt },
      ],
      max_tokens: 2048,
      temperature: 0.9,
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    return Response.json({ error: `LLM error: ${err}` }, { status: 502 });
  }

  const data = await response.json();
  let content = data.choices?.[0]?.message?.content ?? "";

  // Strip thinking tags and markdown fences
  content = content.replace(/<think>[\s\S]*?<\/think>/g, "").trim();
  content = content.replace(/^```(?:json)?\s*/m, "").replace(/\s*```$/m, "").trim();

  let profile;
  try {
    profile = JSON.parse(content);
  } catch {
    return Response.json(
      { error: "Failed to parse queen profile from LLM", raw: content },
      { status: 500 },
    );
  }

  // Save to persona metadata
  persona.queenProfile = profile;
  await savePersonas(personas);

  return Response.json(profile, { status: 201 });
}
