import { NextResponse } from "next/server";
export async function GET() {
  try {
    const res = await fetch("http://192.168.1.189:8760/active-sessions", { next: { revalidate: 15 } });
    return NextResponse.json(await res.json());
  } catch { return NextResponse.json({ sessions: [], count: 0 }); }
}
