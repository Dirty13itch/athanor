import { NextResponse } from "next/server";

export async function POST() {
  try {
    const res = await fetch("http://192.168.1.189:8760/dispatch-and-run", {
      method: "POST",
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
