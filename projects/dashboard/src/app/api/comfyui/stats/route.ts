import { config } from "@/lib/config";

export async function GET() {
  try {
    const res = await fetch(`${config.comfyui.url}/system_stats`, {
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 0 },
    });
    if (!res.ok) {
      return Response.json({ error: "ComfyUI unavailable" }, { status: 502 });
    }
    const data = await res.json();
    return Response.json(data);
  } catch {
    return Response.json({ error: "ComfyUI unreachable" }, { status: 502 });
  }
}
