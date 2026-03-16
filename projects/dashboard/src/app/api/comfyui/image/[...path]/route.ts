import { config } from "@/lib/config";

function guessContentType(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "mp4": return "video/mp4";
    case "webm": return "video/webm";
    case "mov": return "video/quicktime";
    case "webp": return "image/webp";
    case "jpg": case "jpeg": return "image/jpeg";
    case "gif": return "image/gif";
    default: return "image/png";
  }
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  // ComfyUI expects separate filename and subfolder params
  const filename = path[path.length - 1];
  const subfolder = path.length > 1 ? path.slice(0, -1).join("/") : "";

  try {
    const url = new URL(`${config.comfyui.url}/view`);
    url.searchParams.set("filename", filename);
    if (subfolder) url.searchParams.set("subfolder", subfolder);
    url.searchParams.set("type", "output");

    const res = await fetch(url.toString(), {
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) {
      return new Response("Image not found", { status: 404 });
    }

    const contentType = res.headers.get("content-type") ?? guessContentType(filename);
    const contentLength = res.headers.get("content-length");
    const body = res.body;

    const headers: Record<string, string> = {
      "Content-Type": contentType,
      "Cache-Control": "public, max-age=3600",
    };
    if (contentLength) headers["Content-Length"] = contentLength;
    // Videos need Accept-Ranges for seeking
    if (contentType.startsWith("video/")) headers["Accept-Ranges"] = "bytes";

    return new Response(body, { headers });
  } catch {
    return new Response("Failed to fetch image", { status: 502 });
  }
}
