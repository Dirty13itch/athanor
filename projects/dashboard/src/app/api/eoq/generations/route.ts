import { config } from "@/lib/config";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";

interface EoqGeneration {
  promptId: string;
  prompt: string;
  queenName: string;
  type: "portrait" | "scene";
  images: { filename: string; subfolder: string }[];
  timestamp: number;
}

export async function GET() {
  if (isDashboardFixtureMode()) {
    return Response.json({
      generations: [
        {
          promptId: "fixture-1",
          prompt: "Cinematic portrait of Emilie Ekstrom in a ruined throne room.",
          queenName: "Emilie Ekstrom",
          type: "portrait",
          images: [{ filename: "fixture-queen.png", subfolder: "EoBQ" }],
          timestamp: Date.now() / 1000,
        },
      ],
    });
  }

  try {
    const res = await fetch(`${config.comfyui.url}/history`, {
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 0 },
    });
    if (!res.ok) return Response.json({ generations: [] });
    const raw = await res.json();

    const generations: EoqGeneration[] = [];

    for (const [promptId, entry] of Object.entries(raw)) {
      const e = entry as {
        prompt?: [number, string, Record<string, { class_type: string; inputs: Record<string, unknown> }>];
        outputs?: Record<string, { images?: { filename: string; subfolder: string; type: string }[] }>;
      };
      if (!e.outputs) continue;

      const images: { filename: string; subfolder: string }[] = [];
      for (const nodeOutput of Object.values(e.outputs)) {
        if (nodeOutput.images) {
          for (const img of nodeOutput.images) {
            images.push({ filename: img.filename, subfolder: img.subfolder });
          }
        }
      }
      if (images.length === 0) continue;

      // Check if this is an EoBQ generation
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

      // Filter: only EoBQ outputs
      const isEoq =
        outputPrefix.toLowerCase().startsWith("eoq") ||
        images.some((img) => img.subfolder.toLowerCase().startsWith("eoq"));
      if (!isEoq) continue;

      // Extract queen name from prompt (look for known names)
      const queenName = extractQueenName(promptText);
      const type: "portrait" | "scene" = promptText.toLowerCase().includes("portrait") ? "portrait" : "scene";

      generations.push({
        promptId: promptId as string,
        prompt: promptText,
        queenName,
        type,
        images,
        timestamp: e.prompt?.[0] ?? 0,
      });
    }

    generations.sort((a, b) => b.timestamp - a.timestamp);

    return Response.json({ generations: generations.slice(0, 20) });
  } catch {
    return Response.json({ generations: [] });
  }
}

const QUEEN_NAMES = [
  "Emilie Ekstrom", "Jordan Night", "Alanah Rae", "Nikki Benz",
  "Chloe Lamour", "Nicolette Shea", "Peta Jensen", "Sandee Westgate",
  "Marisol Yotta", "Trina Michaels", "Nikki Sexx", "Madison Ivy",
  "Amy Anderssen", "Puma Swede", "Ava Addams", "Brooklyn Chase",
  "Esperanza Gomez", "Savannah Bond", "Shyla Stylez", "Brianna Banks",
  "Clanddi Jinkcebo",
];

function extractQueenName(prompt: string): string {
  for (const name of QUEEN_NAMES) {
    if (prompt.includes(name)) return name;
  }
  // Try first name only
  for (const name of QUEEN_NAMES) {
    const first = name.split(" ")[0];
    if (prompt.includes(first)) return name;
  }
  return "Unknown";
}
