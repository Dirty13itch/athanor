import { NextResponse } from "next/server";
import { listAllContainers } from "@/lib/docker";

export async function GET() {
  try {
    const containers = await listAllContainers();
    const mapped = containers.map((c) => ({
      id: c.Id.slice(0, 12),
      name: c.Names[0]?.replace(/^\//, "") ?? c.Id.slice(0, 12),
      image: c.Image,
      state: c.State,
      status: c.Status,
      created: new Date(c.Created * 1000).toISOString(),
      node: c.node,
    }));
    return NextResponse.json(mapped);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Docker API error" },
      { status: 500 }
    );
  }
}
