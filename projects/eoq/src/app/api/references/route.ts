import { readFile, writeFile, mkdir, rm } from "fs/promises";
import { join } from "path";
import { existsSync } from "fs";

const REFERENCES_DIR = process.env.REFERENCES_DIR ?? "/references";
const METADATA_FILE = join(REFERENCES_DIR, "personas.json");

export interface Persona {
  id: string;
  name: string;
  category: "queens" | "custom";
  folder: string;
  photos: string[];
  createdAt: string;
}

async function loadPersonas(): Promise<Persona[]> {
  try {
    const raw = await readFile(METADATA_FILE, "utf-8");
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

async function savePersonas(personas: Persona[]): Promise<void> {
  await mkdir(REFERENCES_DIR, { recursive: true });
  await writeFile(METADATA_FILE, JSON.stringify(personas, null, 2));
}

/** GET /api/references — list all personas */
export async function GET() {
  const personas = await loadPersonas();
  return Response.json(personas);
}

/** POST /api/references — create a persona */
export async function POST(req: Request) {
  const { name, category } = await req.json() as { name: string; category: "queens" | "custom" };

  if (!name || !category) {
    return Response.json({ error: "name and category required" }, { status: 400 });
  }

  const id = `${category}-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now()}`;
  const folder = id;
  const personaDir = join(REFERENCES_DIR, folder);

  await mkdir(personaDir, { recursive: true });

  const personas = await loadPersonas();
  const newPersona: Persona = { id, name, category, folder, photos: [], createdAt: new Date().toISOString() };
  personas.push(newPersona);
  await savePersonas(personas);

  return Response.json(newPersona, { status: 201 });
}
