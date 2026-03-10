import { config } from "@/lib/config";
import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";
import { getFixtureGalleryImages } from "@/lib/fixtures";
import { NextResponse } from "next/server";

// Known EoBQ characters for name detection from prompts
const CHARACTER_NAMES = ["Isolde", "Seraphine", "Valeria", "Lilith", "Mireille"];

export interface GalleryImage {
  promptId: string;
  filename: string;
  subfolder: string;
  type: "portrait" | "scene" | "unknown";
  character: string | null;
  imageUrl: string;
  timestamp: number;
}

function detectCharacter(promptText: string): string | null {
  for (const name of CHARACTER_NAMES) {
    if (promptText.includes(name)) return name;
  }
  return null;
}

function detectType(promptText: string): GalleryImage["type"] {
  const lower = promptText.toLowerCase();
  if (lower.includes("portrait") || lower.includes("face") || lower.includes("close-up")) {
    return "portrait";
  }
  if (lower.includes("scene") || lower.includes("interior") || lower.includes("exterior") || lower.includes("room")) {
    return "scene";
  }
  return "unknown";
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const character = searchParams.get("character");
  const type = searchParams.get("type");
  const limit = parseInt(searchParams.get("limit") ?? "50", 10);

  if (EOQ_FIXTURE_MODE) {
    let images = getFixtureGalleryImages();
    if (character) {
      images = images.filter((image) => image.character === character);
    }
    if (type) {
      images = images.filter((image) => image.type === type);
    }
    return NextResponse.json({
      images: images.slice(0, limit),
      total: images.length,
      characters: CHARACTER_NAMES,
    });
  }

  try {
    const resp = await fetch(`${config.comfyuiUrl}/history?max_items=200`, {
      next: { revalidate: 30 },
    });

    if (!resp.ok) {
      return NextResponse.json(
        { error: `ComfyUI history unavailable (${resp.status})` },
        { status: 502 },
      );
    }

    const history = await resp.json() as Record<string, {
      prompt: unknown[];
      outputs: Record<string, { images?: { filename: string; subfolder: string; type: string }[] }>;
      status: { status_str: string; completed: boolean; messages: unknown[] };
    }>;

    const images: GalleryImage[] = [];

    for (const [promptId, item] of Object.entries(history)) {
      if (!item.status?.completed) continue;

      // Extract the prompt text from the workflow — node "3" is CLIPTextEncode
      const workflowNodes = item.prompt?.[2] as Record<string, { inputs?: { text?: string } }> | undefined;
      const promptText = workflowNodes?.["3"]?.inputs?.text ?? "";

      const detectedCharacter = detectCharacter(promptText);
      const detectedType = detectType(promptText);

      for (const nodeOutput of Object.values(item.outputs)) {
        if (!nodeOutput.images) continue;
        for (const img of nodeOutput.images) {
          images.push({
            promptId,
            filename: img.filename,
            subfolder: img.subfolder,
            type: detectedType,
            character: detectedCharacter,
            imageUrl: `${config.comfyuiUrl}/view?filename=${encodeURIComponent(img.filename)}&subfolder=${encodeURIComponent(img.subfolder)}&type=${img.type}`,
            // ComfyUI filenames often contain a timestamp prefix (e.g. ComfyUI_00001_)
            timestamp: parseInt(img.filename.replace(/\D/g, "").slice(0, 13), 10) || 0,
          });
        }
      }
    }

    // Sort newest first (by filename sequence number as proxy)
    images.sort((a, b) => b.filename.localeCompare(a.filename));

    // Apply filters
    let filtered = images;
    if (character) {
      filtered = filtered.filter((img) => img.character === character);
    }
    if (type) {
      filtered = filtered.filter((img) => img.type === type);
    }

    return NextResponse.json({
      images: filtered.slice(0, limit),
      total: filtered.length,
      characters: CHARACTER_NAMES,
    });
  } catch (err) {
    console.error("GET /api/gallery error:", err);
    return NextResponse.json({ error: "Failed to fetch gallery" }, { status: 500 });
  }
}
