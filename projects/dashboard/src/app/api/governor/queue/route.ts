import { NextResponse } from "next/server";

export async function GET() {
  try {
    const [stats, queue, attention] = await Promise.all([
      fetch("http://192.168.1.189:8760/stats", { next: { revalidate: 10 } }).then(r => r.json()).catch(() => null),
      fetch("http://192.168.1.189:8760/queue", { next: { revalidate: 10 } }).then(r => r.json()).catch(() => null),
      fetch("http://192.168.1.189:8760/attention", { next: { revalidate: 30 } }).then(r => r.json()).catch(() => null),
    ]);
    return NextResponse.json({ stats, queue: queue?.tasks ?? [], attention: attention?.items ?? [] });
  } catch {
    return NextResponse.json({ stats: null, queue: [], attention: [] });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch("http://192.168.1.189:8760/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
