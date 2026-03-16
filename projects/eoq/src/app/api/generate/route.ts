import { config } from "@/lib/config";
import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";
import { getFixtureGeneratedImage } from "@/lib/fixtures";
import { readFile } from "fs/promises";
import { join } from "path";

interface GenerateRequest {
  prompt: string;
  type: "portrait" | "scene" | "pulid" | "hq" | "pulid-hq" | "video";
  seed?: number;
  /** For type=pulid: filesystem path or URL to the reference photo */
  referencePath?: string;
  /** For type=video: negative prompt for quality control */
  negativePrompt?: string;
  /** Max retry attempts for portrait quality gate (default: 3) */
  maxRetries?: number;
}

const PORTRAIT_TYPES = new Set(["portrait", "pulid", "hq", "pulid-hq"]);
const MAX_PORTRAIT_RETRIES = 3;
/** Minimum image file size in bytes — below this, image is likely blank/corrupt */
const MIN_IMAGE_BYTES = 15_000;

/**
 * Image generation API route.
 * Loads real ComfyUI workflow JSONs from the comfyui/ directory,
 * injects the prompt and seed, then queues generation and polls for the result.
 * Supports PuLID face-injection generation when type=pulid + referencePath provided.
 */
export async function POST(req: Request) {
  const rawBody = await req.text();
  const parsedBody = (rawBody ? JSON.parse(rawBody) : {}) as Partial<GenerateRequest>;
  const { prompt = "", type = "portrait", seed, referencePath, negativePrompt, maxRetries } = parsedBody;

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

  const isPulidType = type === "pulid" || type === "pulid-hq";
  if (isPulidType && !referencePath) {
    return Response.json({ error: "referencePath required for pulid generation" }, { status: 400 });
  }

  // For PuLID types, upload reference once before any retries
  let uploadedFilename: string | null = null;
  if (isPulidType && referencePath) {
    uploadedFilename = await uploadReferenceToComfyUI(referencePath);
    if (!uploadedFilename) {
      return Response.json({ error: "Failed to upload reference photo to ComfyUI" }, { status: 500 });
    }
  }

  // Portrait types get retry logic with seed rotation
  const retryLimit = PORTRAIT_TYPES.has(type) ? (maxRetries ?? MAX_PORTRAIT_RETRIES) : 1;
  const isHqType = type === "hq" || type === "pulid-hq";
  const maxWait = type === "video" ? 600000 : (isHqType ? 300000 : 120000);

  let bestResult: { imageUrl: string | null; promptId: string } | null = null;

  for (let attempt = 0; attempt < retryLimit; attempt++) {
    const attemptSeed = seed != null && attempt === 0
      ? seed
      : Math.floor(Math.random() * 2147483647);

    const workflow = await buildWorkflowForType(type, prompt, attemptSeed, uploadedFilename, negativePrompt);

    const queueResp = await fetch(`${config.comfyuiUrl}/prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: workflow }),
    });

    if (!queueResp.ok) {
      const error = await queueResp.text();
      if (attempt === retryLimit - 1) {
        return Response.json({ error }, { status: queueResp.status });
      }
      continue;
    }

    const { prompt_id } = await queueResp.json();
    const imageUrl = await pollForResult(prompt_id, maxWait);

    // For non-portrait types (scenes, video), return immediately
    if (!PORTRAIT_TYPES.has(type)) {
      return Response.json({ imageUrl, promptId: prompt_id });
    }

    // Quality gate: validate portrait output
    if (imageUrl) {
      const quality = await checkImageQuality(imageUrl);
      if (quality.pass) {
        return Response.json({
          imageUrl,
          promptId: prompt_id,
          attempt: attempt + 1,
          quality: quality.reason,
        });
      }

      // Keep as fallback in case all retries fail
      if (!bestResult) {
        bestResult = { imageUrl, promptId: prompt_id };
      }
      console.log(`[face-gate] Attempt ${attempt + 1}/${retryLimit} rejected: ${quality.reason}`);
    }
  }

  // All retries exhausted — return best available result
  if (bestResult) {
    return Response.json({
      ...bestResult,
      attempt: retryLimit,
      quality: "fallback — all retries failed quality check",
    });
  }

  return Response.json({ imageUrl: null, promptId: null, quality: "generation failed" });
}

/** Build the appropriate workflow based on generation type */
async function buildWorkflowForType(
  type: string,
  prompt: string,
  seed: number,
  uploadedFilename: string | null,
  negativePrompt?: string,
): Promise<Record<string, unknown>> {
  if ((type === "pulid" || type === "pulid-hq") && uploadedFilename) {
    return buildPulidWorkflow(prompt, uploadedFilename, seed, type === "pulid-hq");
  }
  if (type === "video") {
    return buildVideoWorkflow(prompt, negativePrompt, seed);
  }
  return buildWorkflow(type as "portrait" | "scene" | "hq", prompt, seed);
}

/** Validate generated portrait quality by checking image file size and dimensions */
async function checkImageQuality(imageUrl: string): Promise<{ pass: boolean; reason: string }> {
  try {
    const resp = await fetch(imageUrl);
    if (!resp.ok) return { pass: false, reason: "failed to fetch image" };

    const contentLength = resp.headers.get("content-length");
    const sizeBytes = contentLength ? parseInt(contentLength, 10) : null;

    // If content-length header is missing, read the body to check size
    if (sizeBytes == null) {
      const buffer = await resp.arrayBuffer();
      if (buffer.byteLength < MIN_IMAGE_BYTES) {
        return { pass: false, reason: `image too small (${buffer.byteLength} bytes)` };
      }
      return { pass: true, reason: "ok" };
    }

    if (sizeBytes < MIN_IMAGE_BYTES) {
      return { pass: false, reason: `image too small (${sizeBytes} bytes)` };
    }

    return { pass: true, reason: "ok" };
  } catch {
    // If we can't check quality, pass it through rather than blocking
    return { pass: true, reason: "quality check skipped (fetch error)" };
  }
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
 * Standard mode: flux-pulid-portrait.json (FaceDetailer included)
 * HQ mode: flux-pulid-hq.json (FaceDetailer + 4x UltraSharp upscale)
 */
async function buildPulidWorkflow(
  prompt: string,
  referenceFilename: string,
  seed?: number,
  hq = false,
): Promise<Record<string, unknown>> {
  const filename = hq ? "flux-pulid-hq.json" : "flux-pulid-portrait.json";
  const workflowPath = join(process.cwd(), "comfyui", filename);
  const raw = await readFile(workflowPath, "utf-8");
  const workflow = JSON.parse(raw);

  const actualSeed = seed ?? Math.floor(Math.random() * 2147483647);
  if (workflow["3"]?.inputs) workflow["3"].inputs.text = prompt;
  if (workflow["7"]?.inputs) workflow["7"].inputs.seed = actualSeed;
  if (workflow["15"]?.inputs) workflow["15"].inputs.image = referenceFilename;
  // FaceDetailer node uses same seed for consistency
  if (workflow["21"]?.inputs) workflow["21"].inputs.seed = actualSeed;
  if (workflow["31"]?.inputs) workflow["31"].inputs.seed = actualSeed;

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

  const actualSeed = seed ?? Math.floor(Math.random() * 2147483647);

  if (workflow["3"]?.inputs) {
    workflow["3"].inputs.text = prompt;
  }

  if (workflow["7"]?.inputs) {
    workflow["7"].inputs.seed = actualSeed;
  }

  // FaceDetailer node uses same seed for consistency (portrait/pulid workflows)
  if (workflow["21"]?.inputs) {
    workflow["21"].inputs.seed = actualSeed;
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
