import { NextResponse } from "next/server";
import { isDockerAvailable, listContainers } from "@/lib/docker";

export async function GET() {
  if (!isDockerAvailable()) {
    return NextResponse.json(
      { error: "Docker socket not available" },
      { status: 503 }
    );
  }

  try {
    const containers = await listContainers();
    const mapped = containers.map((c) => ({
      id: c.Id.slice(0, 12),
      name: c.Names[0]?.replace(/^\//, "") ?? c.Id.slice(0, 12),
      image: c.Image,
      state: c.State,
      status: c.Status,
      created: new Date(c.Created * 1000).toISOString(),
    }));
    return NextResponse.json(mapped);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Docker API error" },
      { status: 500 }
    );
  }
}
