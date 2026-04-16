import { readFile } from "fs/promises";
import { join } from "path";
import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";

const REFERENCES_DIR = process.env.REFERENCES_DIR ?? "/references";
const METADATA_FILE = join(REFERENCES_DIR, "personas.json");

interface PersonaEntry {
  id: string;
  name: string;
  category: string;
  folder: string;
  photos: string[];
  createdAt: string;
  queenProfile?: Record<string, unknown>;
}

/**
 * GET /api/queens/custom
 * Returns all personas that have a generated queen profile.
 * Used by the queen roster to merge custom queens with hardcoded ones.
 */
export async function GET() {
  if (EOQ_FIXTURE_MODE) {
    return Response.json([]);
  }

  try {
    const raw = await readFile(METADATA_FILE, "utf-8");
    const personas: PersonaEntry[] = JSON.parse(raw);
    const queens = personas
      .filter((p) => p.queenProfile)
      .map((p) => ({
        personaId: p.id,
        photoCount: p.photos.length,
        ...p.queenProfile,
      }));
    return Response.json(queens);
  } catch {
    return Response.json([]);
  }
}
