/**
 * SoulForge API route — generate a Legacy Daughter
 *
 * POST /api/soulforge
 * Body: { motherId, generation?, tasteDescriptor?, inheritedPath? }
 *
 * Returns the generated LegacyDaughter object and a ComfyUI workflow payload
 * ready to submit to WORKSHOP:8188 for portrait generation.
 */

import { config } from "@/lib/config";
import { forgeDaughter, buildSoulForgeComfyPayload } from "@/lib/soulforge";
import { CHARACTERS } from "@/data/characters";
import type { PlayerTaste } from "@/lib/soulforge";

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  if (!body?.motherId) {
    return Response.json({ error: "motherId required" }, { status: 400 });
  }

  const { motherId, generation = 1, tasteDescriptor = "", inheritedPath } = body;

  // Get mother character
  const mother = CHARACTERS[motherId];
  if (!mother) {
    return Response.json({ error: `Unknown character: ${motherId}` }, { status: 404 });
  }

  if (!mother.dna) {
    return Response.json(
      { error: `${motherId} has no DNA — only council queens can forge daughters` },
      { status: 400 }
    );
  }

  // Parse taste descriptor into bias object
  const taste: PlayerTaste = parseTasteDescriptor(tasteDescriptor);

  // Generate the daughter
  const daughter = forgeDaughter(
    motherId,
    mother.dna,
    mother.personality,
    mother.visualDescription,
    generation,
    taste,
    inheritedPath as "craves" | "fights" | undefined
  );

  // Build ComfyUI workflow payload
  // LoRA path convention: /models/lora/queens/{motherId}.safetensors
  const motherLoraPath = `queens/${motherId}.safetensors`;
  const comfyPayload = buildSoulForgeComfyPayload(daughter, motherLoraPath);

  // Optionally submit to ComfyUI directly (fire and forget)
  let comfyJobId: string | null = null;
  try {
    const comfyResp = await fetch(`${config.comfyuiUrl}/prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(comfyPayload),
      signal: AbortSignal.timeout(10_000),
    });
    if (comfyResp.ok) {
      const comfyData = await comfyResp.json();
      comfyJobId = comfyData.prompt_id ?? null;
    }
  } catch {
    // ComfyUI unavailable — return daughter data without portrait
  }

  return Response.json({
    daughter,
    comfyJobId,
    message: comfyJobId
      ? `Portrait generation queued (job: ${comfyJobId}). Poll /api/generate?job=${comfyJobId} for result.`
      : "Daughter generated. ComfyUI unavailable — portrait queued when connection restored.",
  });
}

/**
 * Parse a free-text taste descriptor into structured bias values.
 * Examples: "tall, fake, submissive discovery" → high exhibitionism, responsive desire
 */
function parseTasteDescriptor(descriptor: string): PlayerTaste {
  const lower = descriptor.toLowerCase();
  const taste: PlayerTaste = { descriptor };

  // Submission signals
  if (/submissive|surrender|obedient|yielding/.test(lower)) {
    taste.submissionBias = 3;
    taste.awakeningBias = "slow-realization";
  }

  // Exhibitionism signals
  if (/exhib|public|watch|stage|perform|cam|show/.test(lower)) {
    taste.exhibitionismBias = 3;
  }

  // Pain signals
  if (/pain|rough|hard|hurt|punish|masoch/.test(lower)) {
    taste.painBias = 3;
  }

  // Humiliation signals
  if (/humiliat|shame|degrade|embarrass/.test(lower)) {
    taste.humiliationBias = 3;
  }

  // Addiction speed signals
  if (/instant|immediate|fast|quick|obsess/.test(lower)) {
    taste.addictionBias = "instant";
  } else if (/slow|gradual|patient/.test(lower)) {
    taste.addictionBias = "slow-burn";
  }

  // Awakening type signals
  if (/surprise|shock|unexpected/.test(lower)) {
    taste.awakeningBias = "total-surprise";
  } else if (/denial|forced|resist/.test(lower)) {
    taste.awakeningBias = "denial-until-forced";
  } else if (/always knew|eager|ready/.test(lower)) {
    taste.awakeningBias = "always-knew";
  }

  return taste;
}
