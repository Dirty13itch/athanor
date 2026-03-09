import { readFile, writeFile, rm } from "fs/promises";
import { join } from "path";

const REFERENCES_DIR = process.env.REFERENCES_DIR ?? "/references";
const METADATA_FILE = join(REFERENCES_DIR, "personas.json");

async function loadPersonas() {
  try {
    const raw = await readFile(METADATA_FILE, "utf-8");
    return JSON.parse(raw) as Array<{ id: string; name: string; category: string; folder: string; photos: string[]; createdAt: string }>;
  } catch {
    return [];
  }
}

async function savePersonas(personas: unknown[]) {
  await writeFile(METADATA_FILE, JSON.stringify(personas, null, 2));
}

/** DELETE /api/references/[id] — delete a persona and all photos */
export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const personas = await loadPersonas();
  const persona = personas.find((p) => p.id === id);
  if (!persona) return Response.json({ error: "Not found" }, { status: 404 });

  const personaDir = join(REFERENCES_DIR, persona.folder);
  await rm(personaDir, { recursive: true, force: true });

  const updated = personas.filter((p) => p.id !== id);
  await savePersonas(updated);

  return Response.json({ ok: true });
}
