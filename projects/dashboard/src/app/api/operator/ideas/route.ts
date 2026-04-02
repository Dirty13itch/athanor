import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const query = params.toString();
  return proxyAgentJson(`/v1/operator/ideas${query ? `?${query}` : ""}`, undefined, "Failed to fetch operator ideas");
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, "/v1/operator/ideas", "Failed to create operator idea", {
    privilegeClass: "operator",
    defaultReason: "Created operator idea from dashboard",
    bodyOverride: {
      title: (body as { title?: unknown }).title ?? "",
      note: (body as { note?: unknown }).note ?? "",
      tags: (body as { tags?: unknown }).tags ?? [],
      source: (body as { source?: unknown }).source ?? "dashboard",
      confidence: (body as { confidence?: unknown }).confidence ?? 0.5,
      energy_class: (body as { energy_class?: unknown }).energy_class ?? "focused",
      scope_guess: (body as { scope_guess?: unknown }).scope_guess ?? "global",
      next_review_at: (body as { next_review_at?: unknown }).next_review_at ?? null,
      metadata: (body as { metadata?: unknown }).metadata ?? {},
      reason: (body as { reason?: unknown }).reason ?? "Created operator idea from dashboard",
    },
  });
}
