import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  const { messages, model, backendUrl } = await req.json();

  if (!backendUrl) {
    return new Response("Missing backendUrl", { status: 400 });
  }

  const upstream = await fetch(`${backendUrl}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: model ?? "default",
      messages,
      max_tokens: 2048,
      temperature: 0.7,
      stream: true,
    }),
  });

  if (!upstream.ok) {
    const text = await upstream.text();
    return new Response(text, { status: upstream.status });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
