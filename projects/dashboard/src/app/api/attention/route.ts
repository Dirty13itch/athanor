import { NextResponse } from "next/server";

export async function GET() {
  try {
    const res = await fetch("http://192.168.1.189:8760/attention", {
      next: { revalidate: 30 },
    });
    if (!res.ok) {
      return NextResponse.json({ attention_count: 0, total_items: 0, items: [] });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ attention_count: 0, total_items: 0, items: [] });
  }
}
