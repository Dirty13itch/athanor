import { config } from "@/lib/config";
import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";
import { getFixtureGeneratedImage } from "@/lib/fixtures";
import { readFile } from "fs/promises";
import { join } from "path";

interface GenerateRequest {
  prompt: string;
  type: "portrait" | "scene" | "pulid" | "hq" | "video";
  seed?: number;
  /** For type=pulid: filesystem path or URL to the reference photo */
  referencePath?: string;
  /** For type=video: negative prompt for quality control */
  negativePrompt?: string;
}

/**
 * Image generation API route.
 * Loads real ComfyUI workflow JSONs from the comfyui/ directory,
 * injects the prompt and seed, then queues generation and polls for the result.
 * Supports PuLID face-injection generation when type=pulid + referencePath provided.
 */
export async function POST(req: Request) {
  const rawBody = await req.text();
  const parsedBody = (rawBody ? JSON.parse(rawBody) : {}) as Partial<GenerateRequest>;
  const { prompt = "", type = "portrait", seed, referencePath, negativePrompt } = parsedBody;

  if (EOQ_FIXTURE_MODE) {
    const label =
      type === "scene"
        ? "Fixture Scene"
        : type === "pulid"
          ? "Fixture PuLID Portrait"
          : "Fixture Portrait";
    return Response.json({
      imageUrl: getFixtureGeneratedImage(label, type === "scene" ? "#2563eb" : "#ec4899"),
      promptId: `fixture-${type}-${seed ?? "seedless"}`,
      referencePath,
      prompt,
    });
  }

  let workflow: Record<string, unknown>;

  if (type === "pulid") {
    if (!referencePath) {
      return Response.json({ error: "referencePath required for pulid generation" }, { status: 400 });
    }
    // Upload reference photo to ComfyUI input, then build PuLID workflow
    const uploadedFilename = await uploadReferenceToComfyUI(referencePath);
    if (!uploadedFilename) {
      return Response.json({ error: "Failed to upload reference photo to ComfyUI" }, { status: 500 });
    }
    workflow = await buildPulidWorkflow(prompt, uploadedFilename, seed);
  } else if (type === "video") {
    workflow = await buildVideoWorkflow(prompt, negativePrompt, seed);
  } else {
    workflow = await buildWorkflow(type, prompt, seed);
  }

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

  // Poll for completion — videos take longer (~4 min vs ~1 min for images)
  const maxWait = type === "video" ? 600000 : (type === "hq" ? 300000 : 120000);
  const imageUrl = await pollForResult(prompt_id, maxWait);

  return Response.json({ imageUrl, promptId: prompt_id });
}

/**
 * Upload a reference photo to ComfyUI's input directory.
 * Accepts both local file paths and URLs (e.g., Stash performer images).
 * Returns the filename ComfyUI assigned (use in LoadImage node).
 */
async function uploadReferenceToComfyUI(referencePath: string): Promise<string | null> {
  try {
    let fileData: ArrayBuffer;
    let filename: string;

    if (referencePath.startsWith("http://") || referencePath.startsWith("https://")) {
      // Fetch from URL (e.g., Stash performer profile image)
      const resp = await fetch(referencePath);
      if (!resp.ok) return null;
      fileData = await resp.arrayBuffer();
      // Extract filename from URL or generate one
      const urlPath = new URL(referencePath).pathname;
      filename = urlPath.split("/").pop() ?? "reference.jpg";
      if (!filename.includes(".")) filename += ".jpg";
    } else {
      // Read from local filesystem
      const buf = await readFile(referencePath);
      fileData = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
      filename = referencePath.split("/").pop() ?? "reference.jpg";
    }

    const form = new FormData();
    form.append("image", new Blob([fileData], { type: "image/jpeg" }), filename);
    form.append("overwrite", "true");

    const resp = await fetch(`${config.comfyuiUrl}/upload/image`, {
      method: "POST",
      body: form,
    });

    if (!resp.ok) return null;
    const data = await resp.json();
    return data.name ?? null;
  } catch {
    return null;
  }
}

/**
 * Build a PuLID face-injection workflow.
 * Loads flux-pulid-portrait.json and injects the prompt, seed, and reference image filename.
 */
async function buildPulidWorkflow(
  prompt: string,
  referenceFilename: string,
  seed?: number
): Promise<Record<string, unknown>> {
  const workflowPath = join(process.cwd(), "comfyui", "flux-pulid-portrait.json");
  const raw = await readFile(workflowPath, "utf-8");
  const workflow = JSON.parse(raw);

  if (workflow["3"]?.inputs) workflow["3"].inputs.text = prompt;
  if (workflow["7"]?.inputs) workflow["7"].inputs.seed = seed ?? Math.floor(Math.random() * 2147483647);
  if (workflow["15"]?.inputs) workflow["15"].inputs.image = referenceFilename;

  return workflow;
}

/**
 * Load a ComfyUI workflow template and inject prompt + seed.
 * Templates live in projects/eoq/comfyui/*.json
 */
async function buildWorkflow(
  type: "portrait" | "scene" | "hq",
  prompt: string,
  seed?: number
): Promise<Record<string, unknown>> {
  const filename = type === "hq"
    ? "flux-portrait-hq.json"
    : type === "portrait"
      ? "flux-character-portrait.json"
      : "flux-scene.json";

  const workflowPath = join(process.cwd(), "comfyui", filename);
  const raw = await readFile(workflowPath, "utf-8");
  const workflow = JSON.parse(raw);

  if (workflow["3"]?.inputs) {
    workflow["3"].inputs.text = prompt;
  }

  if (workflow["7"]?.inputs) {
    workflow["7"].inputs.seed = seed ?? Math.floor(Math.random() * 2147483647);
  }

  return workflow;
}

/**
 * Build Wan2.2 T2V video workflow from template.
 * Requires 5090 GPU (14B model doesn't fit on 16GB cards).
 */
async function buildVideoWorkflow(
  prompt: string,
  negativePrompt?: string,
  seed?: number
): Promise<Record<string, unknown>> {
  const workflowPath = join(process.cwd(), "comfyui", "wan-t2v.json");
  const raw = await readFile(workflowPath, "utf-8");
  const workflow = JSON.parse(raw);

  // Inject prompt into WanVideoTextEncode node
  if (workflow["2"]?.inputs) {
    workflow["2"].inputs.positive_prompt = prompt;
    if (negativePrompt) {
      workflow["2"].inputs.negative_prompt = negativePrompt;
    }
  }

  // Inject seed into WanVideoSampler node
  if (workflow["5"]?.inputs) {
    workflow["5"].inputs.seed = seed ?? Math.floor(Math.random() * 2147483647);
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

    // Check for error status
    if (result.status?.status_str === "error") return null;

    for (const nodeOutput of Object.values(result.outputs) as Array<Record<string, unknown>>) {
      // Check images (portraits, scenes, HQ), videos (mp4), and gifs (animated previews)
      for (const key of ["images", "videos", "gifs"] as const) {
        const files = nodeOutput[key] as Array<{ filename: string; subfolder: string; type: string }> | undefined;
        if (files?.[0]) {
          const f = files[0];
          return `${config.comfyuiUrl}/view?filename=${f.filename}&subfolder=${f.subfolder}&type=${f.type}`;
        }
      }
    }
  }

  return null;
}
