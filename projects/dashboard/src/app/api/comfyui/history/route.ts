import { config } from "@/lib/config";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";

export interface ComfyUIHistoryItem {
  promptId: string;
  prompt: string;
  outputImages: { filename: string; subfolder: string; type: string }[];
  timestamp: number;
  outputPrefix: string;
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const maxItems = parseInt(searchParams.get("max_items") ?? "20");

  if (isDashboardFixtureMode()) {
    return Response.json({
      items: [
        {
          promptId: "fixture-history-1",
          prompt: "Cinematic portrait of a queen in a ruined throne room.",
          outputImages: [{ filename: "fixture-queen.png", subfolder: "EoBQ", type: "output" }],
          timestamp: Date.now(),
          outputPrefix: "EoBQ/character",
        },
      ].slice(0, maxItems),
    });
  }

  try {
    const res = await fetch(`${config.comfyui.url}/history`, {
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 0 },
    });
    if (!res.ok) {
      return Response.json({ items: [] });
    }
    const raw = await res.json();

    const items: ComfyUIHistoryItem[] = [];

    for (const [promptId, entry] of Object.entries(raw)) {
      const e = entry as {
        prompt?: [number, string, Record<string, { class_type: string; inputs: Record<string, unknown> }>];
        outputs?: Record<string, { images?: { filename: string; subfolder: string; type: string }[] }>;
      };
      if (!e.outputs) continue;

      // Extract output images
      const outputImages: { filename: string; subfolder: string; type: string }[] = [];
      for (const nodeOutput of Object.values(e.outputs)) {
        if (nodeOutput.images) {
          outputImages.push(...nodeOutput.images);
        }
      }
      if (outputImages.length === 0) continue;

      // Extract prompt text from CLIPTextEncode nodes
      let promptText = "";
      let outputPrefix = "";
      const workflow = e.prompt?.[2];
      if (workflow) {
        for (const node of Object.values(workflow)) {
          if (node.class_type === "CLIPTextEncode" && typeof node.inputs?.text === "string") {
            promptText = node.inputs.text;
          }
          if (node.class_type === "SaveImage" && typeof node.inputs?.filename_prefix === "string") {
            outputPrefix = node.inputs.filename_prefix;
          }
        }
      }

      items.push({
        promptId: promptId as string,
        prompt: promptText,
        outputImages,
        timestamp: e.prompt?.[0] ?? 0,
        outputPrefix,
      });
    }

    // Sort by timestamp descending, limit
    items.sort((a, b) => b.timestamp - a.timestamp);

    return Response.json({ items: items.slice(0, maxItems) });
  } catch {
    return Response.json({ items: [] });
  }
}
