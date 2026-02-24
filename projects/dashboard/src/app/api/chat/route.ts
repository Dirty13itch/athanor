import { NextRequest } from "next/server";

const LITELLM_URL = "http://192.168.1.203:4000";
const LITELLM_API_KEY = "sk-athanor-litellm-2026";

export async function POST(req: NextRequest) {
  const { messages, model, backendUrl } = await req.json();

  if (!backendUrl) {
    return new Response("Missing backendUrl", { status: 400 });
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (backendUrl.startsWith(LITELLM_URL)) {
    headers["Authorization"] = `Bearer ${LITELLM_API_KEY}`;
  }

  const upstream = await fetch(`${backendUrl}/v1/chat/completions`, {
    method: "POST",
    headers,
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
