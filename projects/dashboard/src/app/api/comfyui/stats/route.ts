import { config } from "@/lib/config";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";

export async function GET() {
  if (isDashboardFixtureMode()) {
    return Response.json({
      system: { os: "fixture-linux", python_version: "3.12" },
      devices: [
        {
          name: "Fixture RTX 4090",
          type: "cuda",
          index: 0,
          vram_total: 24 * 1024 ** 3,
          vram_free: 10 * 1024 ** 3,
        },
      ],
    });
  }

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
