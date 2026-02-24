import { config } from "@/lib/config";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const filename = path.join("/");

  try {
    const url = new URL(`${config.comfyui.url}/view`);
    url.searchParams.set("filename", filename);
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
