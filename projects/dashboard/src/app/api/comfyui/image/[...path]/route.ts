import { config } from "@/lib/config";

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

    const contentType = res.headers.get("content-type") ?? "image/png";
    const body = res.body;

    return new Response(body, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=3600",
      },
    });
  } catch {
    return new Response("Failed to fetch image", { status: 502 });
  }
}
