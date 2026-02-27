import { config } from "@/lib/config";
import { readFile } from "fs/promises";
import { join } from "path";

interface GenerateRequest {
  prompt: string;
  type: "portrait" | "scene";
  seed?: number;
}

/**
 * Image generation API route.
 * Loads real ComfyUI workflow JSONs from the comfyui/ directory,
 * injects the prompt and seed, then queues generation and polls for the result.
 */
export async function POST(req: Request) {
  const { prompt, type, seed }: GenerateRequest = await req.json();

  const workflow = await buildWorkflow(type, prompt, seed);

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

  // Poll for completion
  const imageUrl = await pollForResult(prompt_id);

  return Response.json({ imageUrl, promptId: prompt_id });
}

/**
 * Load a ComfyUI workflow template and inject prompt + seed.
 * Templates live in projects/eoq/comfyui/*.json
 */
async function buildWorkflow(
  type: "portrait" | "scene",
  prompt: string,
  seed?: number
): Promise<Record<string, unknown>> {
  const filename = type === "portrait"
    ? "flux-character-portrait.json"
    : "flux-scene.json";

  const workflowPath = join(process.cwd(), "comfyui", filename);
  const raw = await readFile(workflowPath, "utf-8");
  const workflow = JSON.parse(raw);

  // Inject prompt into CLIPTextEncode node (node "3")
  if (workflow["3"]?.inputs) {
    workflow["3"].inputs.text = prompt;
  }

  // Inject seed into KSampler node (node "7")
  if (workflow["7"]?.inputs) {
    workflow["7"].inputs.seed = seed ?? Math.floor(Math.random() * 2147483647);
  }

  return workflow;
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
