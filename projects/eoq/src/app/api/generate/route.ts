import { config } from "@/lib/config";

interface GenerateRequest {
  prompt: string;
  type: "portrait" | "scene";
  seed?: number;
}

/**
 * Image generation API route.
 * Sends a prompt to ComfyUI and returns the generated image URL.
 * This runs server-side — no CORS issues.
 */
export async function POST(req: Request) {
  const { prompt, type, seed }: GenerateRequest = await req.json();

  // Load the appropriate ComfyUI workflow template
  const workflow = type === "portrait" ? portraitWorkflow(prompt, seed) : sceneWorkflow(prompt, seed);

  // Queue the generation
  const queueResp = await fetch(`${config.comfyuiUrl}/prompt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt: workflow }),
  });

  if (!queueResp.ok) {
    const error = await queueResp.text();
    return Response.json({ error }, { status: queueResp.status });
  }

  const { prompt_id } = await queueResp.json();

  // Poll for completion (simple approach — WebSocket in future)
  const imageUrl = await pollForResult(prompt_id);

  return Response.json({ imageUrl, promptId: prompt_id });
}

async function pollForResult(promptId: string, maxWait = 120000): Promise<string | null> {
  const start = Date.now();

  while (Date.now() - start < maxWait) {
    await new Promise((r) => setTimeout(r, 1000));

    const resp = await fetch(`${config.comfyuiUrl}/history/${promptId}`);
    if (!resp.ok) continue;

    const data = await resp.json();
    const result = data[promptId];
    if (!result?.outputs) continue;

    // Find the first image output
    for (const nodeOutput of Object.values(result.outputs) as Array<Record<string, unknown>>) {
      const images = nodeOutput.images as Array<{ filename: string; subfolder: string; type: string }> | undefined;
      if (images?.[0]) {
        const img = images[0];
        return `${config.comfyuiUrl}/view?filename=${img.filename}&subfolder=${img.subfolder}&type=${img.type}`;
      }
    }
  }

  return null;
}

/** Minimal portrait workflow — placeholder until we load the full ComfyUI workflow JSONs */
function portraitWorkflow(prompt: string, seed?: number) {
  // TODO: Load from projects/eoq/comfyui/flux-character-portrait.json
  // and inject the prompt + seed. For now, return a minimal structure.
  return {
    "3": {
      class_type: "CLIPTextEncode",
      inputs: {
        text: `${prompt}, cinematic, photorealistic, 8k, dramatic lighting, shallow depth of field`,
        clip: ["4", 0],
      },
    },
    // ... rest of workflow nodes would go here
    _placeholder: true,
  };
}

function sceneWorkflow(prompt: string, seed?: number) {
  // TODO: Load from projects/eoq/comfyui/flux-scene.json
  return {
    "3": {
      class_type: "CLIPTextEncode",
      inputs: {
        text: `${prompt}, cinematic, wide shot, 8k, film color grading, deep focus`,
        clip: ["4", 0],
      },
    },
    _placeholder: true,
  };
}
