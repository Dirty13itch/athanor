import { config } from "@/lib/config";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { workflow, prompt: promptText, seed } = body;

    if (!workflow) {
      return Response.json({ error: "Missing workflow" }, { status: 400 });
    }

    // If promptText is provided, inject it into the CLIPTextEncode node (node "3")
    const workflowCopy = JSON.parse(JSON.stringify(workflow));
    if (promptText && workflowCopy["3"]?.inputs) {
      workflowCopy["3"].inputs.text = promptText;
    }
    // If seed is provided, inject it into the KSampler node (node "7")
    if (seed !== undefined && workflowCopy["7"]?.inputs) {
      workflowCopy["7"].inputs.seed = seed;
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
