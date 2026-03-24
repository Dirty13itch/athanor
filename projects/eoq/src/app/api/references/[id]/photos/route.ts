import { readFile, writeFile, mkdir, unlink } from "fs/promises";
import { join } from "path";
import { config } from "@/lib/config";
import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";
import { addFixturePersonaPhoto, removeFixturePersonaPhoto } from "@/lib/fixtures";

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

/**
 * GET /api/references/[id]/photos?filename=xxx
 * Serve a reference photo for thumbnail display.
 */
export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const url = new URL(req.url);
  const filename = url.searchParams.get("filename");
  if (!filename) return Response.json({ error: "filename required" }, { status: 400 });

  const personas = await loadPersonas();
  const persona = personas.find((p) => p.id === id);
  if (!persona) return Response.json({ error: "Persona not found" }, { status: 404 });

  const filepath = join(REFERENCES_DIR, persona.folder, filename.replace(/[^a-zA-Z0-9._-]/g, "_"));
  try {
    const data = await readFile(filepath);
    const ext = filename.split(".").pop()?.toLowerCase() ?? "jpg";
    const mime = ext === "png" ? "image/png" : ext === "webp" ? "image/webp" : "image/jpeg";
    return new Response(data, { headers: { "Content-Type": mime, "Cache-Control": "public, max-age=3600" } });
  } catch {
    return Response.json({ error: "Photo not found" }, { status: 404 });
  }
}

/**
 * POST /api/references/[id]/photos
 * Upload a reference photo. Saves to VAULT references dir and forwards to ComfyUI input.
 * Accepts multipart/form-data with an "image" field.
 */
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  if (EOQ_FIXTURE_MODE) {
    const form = await req.formData();
    const file = form.get("image") as File | null;
    if (!file) {
      return Response.json({ error: "image field required" }, { status: 400 });
    }
    const safeName = addFixturePersonaPhoto(id, file.name);
    if (!safeName) {
      return Response.json({ error: "Persona not found" }, { status: 404 });
    }
    return Response.json({ filename: safeName, path: `/fixtures/${id}/${safeName}` }, { status: 201 });
  }

  const personas = await loadPersonas();
  const personaIdx = personas.findIndex((p) => p.id === id);
  if (personaIdx === -1) return Response.json({ error: "Persona not found" }, { status: 404 });

  const persona = personas[personaIdx];
  const personaDir = join(REFERENCES_DIR, persona.folder);
  await mkdir(personaDir, { recursive: true });

  const form = await req.formData();
  const file = form.get("image") as File | null;
  if (!file) return Response.json({ error: "image field required" }, { status: 400 });

  const bytes = await file.arrayBuffer();
  const buffer = Buffer.from(bytes);

  // Sanitize filename and save to VAULT
  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const dest = join(personaDir, safeName);
  await writeFile(dest, buffer);

  // Also upload to ComfyUI input so LoadImage can find it immediately
  const uploadForm = new FormData();
  uploadForm.append("image", new Blob([buffer], { type: file.type || "image/jpeg" }), safeName);
  uploadForm.append("overwrite", "true");
  fetch(`${config.comfyuiUrl}/upload/image`, { method: "POST", body: uploadForm }).catch(() => {});

  // Update metadata
  if (!persona.photos.includes(safeName)) {
    persona.photos.push(safeName);
    await savePersonas(personas);
  }

  return Response.json({ filename: safeName, path: dest }, { status: 201 });
}

/**
 * DELETE /api/references/[id]/photos?filename=xxx
 * Remove a specific photo from a persona.
 */
export async function DELETE(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const url = new URL(req.url);
  const filename = url.searchParams.get("filename");
  if (!filename) return Response.json({ error: "filename required" }, { status: 400 });

  if (EOQ_FIXTURE_MODE) {
    if (!removeFixturePersonaPhoto(id, filename)) {
      return Response.json({ error: "Persona not found" }, { status: 404 });
    }
    return Response.json({ ok: true });
  }

  const personas = await loadPersonas();
  const personaIdx = personas.findIndex((p) => p.id === id);
  if (personaIdx === -1) return Response.json({ error: "Persona not found" }, { status: 404 });

  const persona = personas[personaIdx];
  const filepath = join(REFERENCES_DIR, persona.folder, filename);

  await unlink(filepath).catch(() => {});

  persona.photos = persona.photos.filter((p) => p !== filename);
  await savePersonas(personas);

  return Response.json({ ok: true });
}
