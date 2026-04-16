import { NextRequest, NextResponse } from "next/server";
import {
  buildOperatorSessionIdCookie,
  buildOperatorSessionCookie,
  clearOperatorSessionIdCookie,
  clearOperatorSessionCookie,
  getOperatorSessionId,
  getOperatorMutationToken,
  hasValidOperatorSession,
  validateOperatorToken,
} from "@/lib/operator-auth";

export async function GET(request: NextRequest) {
  const configured = Boolean(process.env.ATHANOR_DASHBOARD_OPERATOR_TOKEN?.trim());
  const unlocked = configured ? hasValidOperatorSession(request) : true;
  return NextResponse.json({
    configured,
    fixtureMode: process.env.DASHBOARD_FIXTURE_MODE === "1",
    requiresSession: configured,
    unlocked,
    sessionIdPresent: Boolean(getOperatorSessionId(request)),
  });
}

export async function POST(request: NextRequest) {
  const configuredToken = getOperatorMutationToken();
  if (!configuredToken) {
    return NextResponse.json({ ok: true, unlocked: true, configured: false });
  }

  const body = await request.json().catch(() => ({}));
  const bodyToken = (body as { token?: unknown }).token;
  const providedToken =
    typeof bodyToken === "string"
      ? bodyToken.trim()
      : request.headers.get("x-athanor-operator-token")?.trim() ?? "";

  if (!validateOperatorToken(providedToken)) {
    return NextResponse.json(
      { error: "Invalid operator token" },
      { status: 403 }
    );
  }

  const sessionId = crypto.randomUUID();
  const response = NextResponse.json({ ok: true, unlocked: true });
  response.headers.append("Set-Cookie", buildOperatorSessionCookie(configuredToken));
  response.headers.append("Set-Cookie", buildOperatorSessionIdCookie(sessionId));
  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true, locked: true });
  response.headers.append("Set-Cookie", clearOperatorSessionCookie());
  response.headers.append("Set-Cookie", clearOperatorSessionIdCookie());
  return response;
}
