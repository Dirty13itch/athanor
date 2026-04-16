import { config } from "@/lib/config";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";

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

function buildFixturePlaceholder(filename: string) {
  const label = filename.replace(/[<>&"]/g, "");
  const body = `
    <svg xmlns="http://www.w3.org/2000/svg" width="1280" height="960" viewBox="0 0 1280 960">
      <rect width="1280" height="960" fill="#111318"/>
      <rect x="48" y="48" width="1184" height="864" rx="32" fill="#1d2330" stroke="#384358" stroke-width="4"/>
      <text x="96" y="120" fill="#f4f6fb" font-family="ui-monospace, SFMono-Regular, monospace" font-size="32">Athanor fixture media</text>
      <text x="96" y="176" fill="#9aa6bd" font-family="ui-monospace, SFMono-Regular, monospace" font-size="24">${label}</text>
    </svg>
  `.trim();
  return new Response(body, {
    headers: {
      "Content-Type": "image/svg+xml",
      "Cache-Control": "public, max-age=300",
    },
  });
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  // ComfyUI expects separate filename and subfolder params
  const filename = path[path.length - 1];
  const subfolder = path.length > 1 ? path.slice(0, -1).join("/") : "";

  if (isDashboardFixtureMode()) {
    return buildFixturePlaceholder(filename);
  }

  try {
    const url = new URL(`${config.comfyui.url}/view`);
    url.searchParams.set("filename", filename);
    if (subfolder) url.searchParams.set("subfolder", subfolder);
    url.searchParams.set("type", "output");

    const res = await fetch(url.toString(), {
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) {
      return buildFixturePlaceholder(filename);
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
    return buildFixturePlaceholder(filename);
  }
}
