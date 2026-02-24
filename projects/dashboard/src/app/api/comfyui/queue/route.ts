import { config } from "@/lib/config";

export async function GET() {
  try {
    const res = await fetch(`${config.comfyui.url}/queue`, {
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 0 },
    });
    if (!res.ok) {
      return Response.json({ queue_running: [], queue_pending: [] });
    }
    const data = await res.json();
    return Response.json({
      queue_running: data.queue_running ?? [],
      queue_pending: data.queue_pending ?? [],
    });
  } catch {
    return Response.json({ queue_running: [], queue_pending: [] });
  }
}
