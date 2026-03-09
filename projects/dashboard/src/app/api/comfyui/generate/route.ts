import { config } from "@/lib/config";

// Built-in Flux workflow templates (node "3" = positive prompt, "7" = KSampler)
const WORKFLOW_TEMPLATES: Record<string, Record<string, unknown>> = {
  character: {
    "1": { class_type: "UNETLoader", inputs: { unet_name: "flux1-dev-fp8.safetensors", weight_dtype: "fp8_e4m3fn" } },
    "2": { class_type: "DualCLIPLoader", inputs: { clip_name1: "t5xxl_fp8_e4m3fn.safetensors", clip_name2: "clip_l.safetensors", type: "flux" } },
    "3": { class_type: "CLIPTextEncode", inputs: { text: "Cinematic portrait of a beautiful woman with an intense, regal expression. Ornate dark armor with gold filigree. Dimly lit throne room with candlelight. Photorealistic, 8k, dramatic lighting, shallow depth of field.", clip: ["2", 0] } },
    "4": { class_type: "FluxGuidance", inputs: { conditioning: ["3", 0], guidance: 3.5 } },
    "5": { class_type: "CLIPTextEncode", inputs: { text: "", clip: ["2", 0] } },
    "6": { class_type: "EmptySD3LatentImage", inputs: { width: 832, height: 1216, batch_size: 1 } },
    "11": { class_type: "LoraLoaderModelOnly", inputs: { model: ["1", 0], lora_name: "flux-uncensored.safetensors", strength_model: 0.85 } },
    "7": { class_type: "KSampler", inputs: { model: ["11", 0], seed: 42, steps: 25, cfg: 1.0, sampler_name: "euler", scheduler: "simple", positive: ["4", 0], negative: ["5", 0], latent_image: ["6", 0], denoise: 1.0 } },
    "8": { class_type: "VAELoader", inputs: { vae_name: "ae.safetensors" } },
    "9": { class_type: "VAEDecode", inputs: { samples: ["7", 0], vae: ["8", 0] } },
    "10": { class_type: "SaveImage", inputs: { images: ["9", 0], filename_prefix: "EoBQ/character" } },
  },
  scene: {
    "1": { class_type: "UNETLoader", inputs: { unet_name: "flux1-dev-fp8.safetensors", weight_dtype: "fp8_e4m3fn" } },
    "2": { class_type: "DualCLIPLoader", inputs: { clip_name1: "t5xxl_fp8_e4m3fn.safetensors", clip_name2: "clip_l.safetensors", type: "flux" } },
    "3": { class_type: "CLIPTextEncode", inputs: { text: "A grand throne room in a dark fantasy castle. Massive stone pillars, vaulted ceiling. Warm candlelight from iron chandeliers. A throne of black iron and bone. Cinematic wide shot, photorealistic, 8k, dramatic lighting, moody atmosphere.", clip: ["2", 0] } },
    "4": { class_type: "FluxGuidance", inputs: { conditioning: ["3", 0], guidance: 3.5 } },
    "5": { class_type: "CLIPTextEncode", inputs: { text: "", clip: ["2", 0] } },
    "6": { class_type: "EmptySD3LatentImage", inputs: { width: 1344, height: 768, batch_size: 1 } },
    "11": { class_type: "LoraLoaderModelOnly", inputs: { model: ["1", 0], lora_name: "flux-uncensored.safetensors", strength_model: 0.85 } },
    "7": { class_type: "KSampler", inputs: { model: ["11", 0], seed: 123, steps: 25, cfg: 1.0, sampler_name: "euler", scheduler: "simple", positive: ["4", 0], negative: ["5", 0], latent_image: ["6", 0], denoise: 1.0 } },
    "8": { class_type: "VAELoader", inputs: { vae_name: "ae.safetensors" } },
    "9": { class_type: "VAEDecode", inputs: { samples: ["7", 0], vae: ["8", 0] } },
    "10": { class_type: "SaveImage", inputs: { images: ["9", 0], filename_prefix: "EoBQ/scene" } },
  },
};

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { workflow, prompt: promptText, seed } = body;

    if (!workflow) {
      return Response.json({ error: "Missing workflow" }, { status: 400 });
    }

    // If workflow is a string, treat it as a template name and load the built-in template
    let workflowObj: Record<string, unknown>;
    if (typeof workflow === "string") {
      const template = WORKFLOW_TEMPLATES[workflow];
      if (!template) {
        return Response.json({ error: `Unknown workflow type: ${workflow}. Valid types: ${Object.keys(WORKFLOW_TEMPLATES).join(", ")}` }, { status: 400 });
      }
      workflowObj = JSON.parse(JSON.stringify(template));
    } else {
      workflowObj = JSON.parse(JSON.stringify(workflow));
    }

    // If promptText is provided, inject it into the CLIPTextEncode node (node "3")
    const workflowCopy = workflowObj;
    if (promptText && (workflowCopy["3"] as Record<string, Record<string, unknown>>)?.inputs) {
      (workflowCopy["3"] as Record<string, Record<string, unknown>>).inputs.text = promptText;
    }
    // If seed is provided, inject it into the KSampler node (node "7")
    if (seed !== undefined && (workflowCopy["7"] as Record<string, Record<string, unknown>>)?.inputs) {
      (workflowCopy["7"] as Record<string, Record<string, unknown>>).inputs.seed = seed;
    }

    const res = await fetch(`${config.comfyui.url}/prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: workflowCopy }),
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) {
      const text = await res.text();
      return Response.json({ error: text }, { status: res.status });
    }

    const data = await res.json();
    return Response.json(data);
  } catch (e) {
    return Response.json(
      { error: e instanceof Error ? e.message : "Failed to queue generation" },
      { status: 500 }
    );
  }
}
