import { readdir, stat } from "fs/promises";
import { join } from "path";

const OUTPUT_DIR = "/opt/comfyui-output";
const EOQB_SUBFOLDER = "EoBQ";

interface OutputFile {
  filename: string;
  subfolder: string;
  size: number;
  mtime: number;
  isVideo: boolean;
}

/**
 * GET /api/gallery/files — scan ComfyUI output directory directly
 * Returns all files in EoBQ subfolder, ordered by modification time.
 * This supplements the history-based gallery with files whose history was evicted.
 */
export async function GET() {
  try {
    const dir = join(OUTPUT_DIR, EOQB_SUBFOLDER);
    const entries = await readdir(dir);

    const files: OutputFile[] = [];
    for (const entry of entries) {
      const filepath = join(dir, entry);
      const info = await stat(filepath).catch(() => null);
      if (!info || !info.isFile()) continue;

      const ext = entry.split(".").pop()?.toLowerCase() ?? "";
      if (!["png", "jpg", "jpeg", "webp", "mp4", "webm", "mov"].includes(ext)) continue;

      files.push({
        filename: entry,
        subfolder: EOQB_SUBFOLDER,
        size: info.size,
        mtime: Math.floor(info.mtimeMs / 1000),
        isVideo: ["mp4", "webm", "mov"].includes(ext),
      });
    }

    files.sort((a, b) => b.mtime - a.mtime);

    return Response.json({ files });
  } catch (err) {
    return Response.json({
      files: [],
      error: err instanceof Error ? err.message : "Failed to scan output directory",
    });
  }
}
