import { NextRequest } from "next/server";

/**
 * GET /api/gallery/ratings — Fetch all ratings.
 * Optional query: ?filter=approved|flagged|rejected|unrated
 *
 * Currently a stub — ratings are stored client-side in localStorage.
 * When agent server adds GET foundry:9000/v1/gallery/ratings, this will proxy to it.
 */
export async function GET(request: NextRequest) {
  const filter = request.nextUrl.searchParams.get("filter");

  // TODO: Proxy to agent server when GET foundry:9000/v1/gallery/ratings is available
  // const agentUrl = process.env.AGENT_SERVER_URL ?? "http://foundry:9000";
  // const token = process.env.ATHANOR_AGENT_API_TOKEN;
  // const url = filter
  //   ? `${agentUrl}/v1/gallery/ratings?filter=${encodeURIComponent(filter)}`
  //   : `${agentUrl}/v1/gallery/ratings`;
  // const res = await fetch(url, {
  //   headers: { Authorization: `Bearer ${token}` },
  //   next: { revalidate: 0 },
  // });
  // if (!res.ok) throw new Error(`Agent server error: ${res.status}`);
  // return Response.json(await res.json());

  return Response.json({
    ratings: {},
    filter: filter ?? "all",
    source: "localStorage",
    message: "Ratings are stored client-side. This endpoint is a placeholder for agent-server persistence.",
  });
}
