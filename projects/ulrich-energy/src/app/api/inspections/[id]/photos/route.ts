import { NextResponse } from "next/server";
import { queryOne } from "@/lib/db";
import { ULRICH_FIXTURE_MODE } from "@/lib/fixture-mode";
import path from "path";
import { writeFile, mkdir } from "fs/promises";

/**
 * POST /api/inspections/:id/photos
 * Upload a photo for an inspection section.
 *
 * Accepts multipart/form-data with:
 * - photo: File
 * - section: string (building_envelope, blower_door, duct_leakage, insulation, windows, hvac, general)
 * - caption: string (optional)
 *
 * Stores file to /data/photos/:inspectionId/ and updates inspection's photos JSONB array.
 */

const UPLOAD_DIR = process.env.UPLOAD_DIR ?? "/data/photos";
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/heic"]);
const MAX_SIZE = 20 * 1024 * 1024; // 20MB

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  if (ULRICH_FIXTURE_MODE) {
    return NextResponse.json({
      photo: { id: crypto.randomUUID(), filename: "fixture.jpg", section: "general", caption: "" },
    });
  }

  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json({ error: "Invalid form data" }, { status: 400 });
  }

  const file = formData.get("photo") as File | null;
  const section = (formData.get("section") as string) ?? "general";
  const caption = (formData.get("caption") as string) ?? "";

  if (!file || !(file instanceof File)) {
    return NextResponse.json({ error: "photo file is required" }, { status: 400 });
  }

  if (!ALLOWED_TYPES.has(file.type)) {
    return NextResponse.json(
      { error: `Unsupported file type: ${file.type}. Allowed: jpeg, png, webp, heic` },
      { status: 400 },
    );
  }

  if (file.size > MAX_SIZE) {
    return NextResponse.json({ error: "File too large (max 20MB)" }, { status: 400 });
  }

  // Verify inspection exists
  const inspection = await queryOne<{ id: string; photos: unknown[] }>(
    "SELECT id, photos FROM inspections WHERE id = $1",
    [id],
  );
  if (!inspection) {
    return NextResponse.json({ error: "Inspection not found" }, { status: 404 });
  }

  // Save file
  const ext = path.extname(file.name) || ".jpg";
  const photoId = crypto.randomUUID();
  const filename = `${photoId}${ext}`;
  const dir = path.join(UPLOAD_DIR, id);

  try {
    await mkdir(dir, { recursive: true });
    const buffer = Buffer.from(await file.arrayBuffer());
    await writeFile(path.join(dir, filename), buffer);
  } catch (err) {
    console.error("Photo save failed:", err);
    return NextResponse.json({ error: "Failed to save photo" }, { status: 500 });
  }

  // Update inspection photos array
  const photoEntry = {
    id: photoId,
    filename,
    section,
    caption,
    uploadedAt: new Date().toISOString(),
  };

  const photos = [...(inspection.photos ?? []), photoEntry];

  try {
    await queryOne(
      "UPDATE inspections SET photos = $1, updated_at = $2 WHERE id = $3 RETURNING id",
      [JSON.stringify(photos), new Date().toISOString(), id],
    );

    return NextResponse.json({ photo: photoEntry }, { status: 201 });
  } catch (err) {
    console.error("Photo metadata update failed:", err);
    return NextResponse.json({ error: "Failed to update metadata" }, { status: 500 });
  }
}

/**
 * GET /api/inspections/:id/photos
 * List photos for an inspection.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  if (ULRICH_FIXTURE_MODE) {
    return NextResponse.json({ photos: [] });
  }

  const inspection = await queryOne<{ photos: unknown[] }>(
    "SELECT photos FROM inspections WHERE id = $1",
    [id],
  );

  if (!inspection) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  return NextResponse.json({ photos: inspection.photos ?? [] });
}
