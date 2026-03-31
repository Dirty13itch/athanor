import { NextResponse } from "next/server";

export const OPERATOR_SESSION_COOKIE = "athanor_operator_session";
export const OPERATOR_SESSION_ID_COOKIE = "athanor_operator_session_id";
export const OPERATOR_UNLOCK_HEADER = "x-athanor-operator-token";

const PRIVILEGED_MUTATION_PATHS: RegExp[] = [
  /^\/api\/agents\/proxy$/,
  /^\/api\/consolidation$/,
  /^\/api\/gallery\/rate$/,
  /^\/api\/containers\/[^/]+\/restart$/,
  /^\/api\/governor\/(?:pause|resume|presence|release-tier|operator-tests|dispatch|queue)$/,
  /^\/api\/governor\/heartbeat$/,
  /^\/api\/gpu\/swap$/,
  /^\/api\/improvement\/trigger$/,
  /^\/api\/insights\/run$/,
  /^\/api\/learning\/benchmarks$/,
  /^\/api\/models\/proving-ground$/,
  /^\/api\/models\/governance\/promotions(?:\/[^/]+\/(?:advance|hold|rollback))?$/,
  /^\/api\/models\/governance\/retirements(?:\/[^/]+\/(?:advance|hold|rollback))?$/,
  /^\/api\/operator\/context\/(?:agent-threads(?:\/[^/]+)?|direct-chats(?:\/[^/]+)?)$/,
  /^\/api\/operator\/nav-attention$/,
  /^\/api\/operator\/ui-preferences$/,
  /^\/api\/preferences$/,
  /^\/api\/pipeline\/(?:boost|cycle|suppress|react|preview|plans\/[^/]+\/(?:approve|reject))$/,
  /^\/api\/projects\/[^/]+\/(?:advance|state|milestones)$/,
  /^\/api\/push\/send$/,
  /^\/api\/research\/jobs(?:\/[^/]+\/execute)?$/,
  /^\/api\/feedback(?:\/implicit)?$/,
  /^\/api\/skills(?:\/[^/]+(?:\/execution)?)?$/,
  /^\/api\/subscriptions\/(?:execution|leases|handoffs(?:\/[^/]+\/outcome)?)$/,
  /^\/api\/workforce\/(?:conventions\/[^/]+\/(?:confirm|reject)|goals(?:\/[^/]+)?|notifications\/[^/]+\/resolve|plan|redirect|runs|scheduled(?:\/[^/]+\/run)?|tasks(?:\/[^/]+\/(?:approve|cancel|reject))?|workspace\/[^/]+\/endorse)$/,
];

function parseCookies(header: string | null): Map<string, string> {
  const cookies = new Map<string, string>();
  if (!header) {
    return cookies;
  }

  for (const part of header.split(";")) {
    const index = part.indexOf("=");
    if (index < 0) {
      continue;
    }

    const key = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();
    if (key) {
      cookies.set(key, decodeURIComponent(value));
    }
  }

  return cookies;
}

function isLoopbackHost(hostname: string): boolean {
  const normalized = hostname.trim().toLowerCase();
  return normalized === "localhost" || normalized === "127.0.0.1" || normalized === "::1";
}

function originsMatch(candidateOrigin: string, requestOrigin: string): boolean {
  if (candidateOrigin === requestOrigin) {
    return true;
  }

  try {
    const candidate = new URL(candidateOrigin);
    const request = new URL(requestOrigin);
    return (
      candidate.protocol === request.protocol &&
      candidate.port === request.port &&
      isLoopbackHost(candidate.hostname) &&
      isLoopbackHost(request.hostname)
    );
  } catch {
    return false;
  }
}

function isFixtureBypassEnabled(): boolean {
  return (
    process.env.DASHBOARD_FIXTURE_MODE === "1" &&
    process.env.DASHBOARD_REQUIRE_OPERATOR_SESSION !== "1"
  );
}

export function getOperatorMutationToken(): string {
  return (
    process.env.ATHANOR_DASHBOARD_OPERATOR_TOKEN?.trim() ||
    process.env.ATHANOR_AGENT_API_TOKEN?.trim() ||
    ""
  );
}

export function isPrivilegedMutationPath(pathname: string, method: string): boolean {
  if (!/^(POST|PUT|PATCH|DELETE)$/i.test(method)) {
    return false;
  }

  if (!pathname.startsWith("/api/")) {
    return false;
  }

  return PRIVILEGED_MUTATION_PATHS.some((pattern) => pattern.test(pathname));
}

export function hasValidOperatorSession(request: Request): boolean {
  const token = getOperatorMutationToken();
  if (!token) {
    return true;
  }

  const headerToken = request.headers.get(OPERATOR_UNLOCK_HEADER)?.trim();
  if (headerToken === token) {
    return true;
  }

  const cookieToken = parseCookies(request.headers.get("cookie")).get(OPERATOR_SESSION_COOKIE);
  return cookieToken === token;
}

export function hasValidOperatorSessionValue(candidate: string | null | undefined): boolean {
  const token = getOperatorMutationToken();
  if (!token) {
    return true;
  }

  return candidate?.trim() === token;
}

export function getOperatorSessionId(request: Request): string | null {
  return parseCookies(request.headers.get("cookie")).get(OPERATOR_SESSION_ID_COOKIE) ?? null;
}

function hasSameOriginOperatorContext(request: Request): boolean {
  const requestUrl = new URL(request.url);
  const explicitOrigin = request.headers.get("x-athanor-request-origin")?.trim();
  if (explicitOrigin) {
    return originsMatch(explicitOrigin, requestUrl.origin);
  }

  const origin = request.headers.get("origin")?.trim();
  if (origin) {
    return originsMatch(origin, requestUrl.origin);
  }

  const referer = request.headers.get("referer")?.trim();
  if (referer) {
    try {
      return originsMatch(new URL(referer).origin, requestUrl.origin);
    } catch {
      return false;
    }
  }

  const fetchSite = request.headers.get("sec-fetch-site")?.trim().toLowerCase();
  return fetchSite === "same-origin" || fetchSite === "same-site" || fetchSite === "none";
}

export function requireSameOriginOperatorSessionAccess(request: Request): NextResponse | null {
  const sessionGate = requireOperatorSessionAccess(request);
  if (sessionGate) {
    return sessionGate;
  }

  if (hasSameOriginOperatorContext(request)) {
    return null;
  }

  return NextResponse.json(
    {
      error: "Same-origin operator access required",
      gate: "athanor-operator-origin",
    },
    { status: 403 }
  );
}

export function requireOperatorMutationAccess(request: Request): NextResponse | null {
  const pathname = new URL(request.url).pathname;
  if (!isPrivilegedMutationPath(pathname, request.method)) {
    return null;
  }

  if (isFixtureBypassEnabled()) {
    return null;
  }

  const token = getOperatorMutationToken();
  if (!token) {
    if (process.env.NODE_ENV === "production") {
      return NextResponse.json(
        { error: "ATHANOR_DASHBOARD_OPERATOR_TOKEN is required for privileged dashboard mutations" },
        { status: 503 }
      );
    }
    return null;
  }

  const headerToken = request.headers.get(OPERATOR_UNLOCK_HEADER)?.trim();
  if (headerToken === token) {
    return null;
  }

  const cookieToken = parseCookies(request.headers.get("cookie")).get(OPERATOR_SESSION_COOKIE);
  if (cookieToken === token) {
    if (hasSameOriginOperatorContext(request)) {
      return null;
    }

    return NextResponse.json(
      {
        error: "Same-origin operator mutation required",
        gate: "athanor-operator-origin",
      },
      { status: 403 }
    );
  }

  return NextResponse.json(
    {
      error: "Operator session required for privileged dashboard mutation",
      gate: "athanor-operator-session",
    },
    { status: 403 }
  );
}

export function requireOperatorSessionAccess(request: Request): NextResponse | null {
  if (isFixtureBypassEnabled()) {
    return null;
  }

  const token = getOperatorMutationToken();
  if (!token) {
    if (process.env.NODE_ENV === "production") {
      return NextResponse.json(
        { error: "ATHANOR_DASHBOARD_OPERATOR_TOKEN is required for operator session access" },
        { status: 503 }
      );
    }
    return null;
  }

  if (hasValidOperatorSession(request)) {
    return null;
  }

  return NextResponse.json(
    {
      error: "Operator session required",
      gate: "athanor-operator-session",
    },
    { status: 403 }
  );
}

export function buildOperatorSessionCookie(token: string): string {
  return `${OPERATOR_SESSION_COOKIE}=${encodeURIComponent(token)}; Path=/; HttpOnly; SameSite=Strict${
    process.env.NODE_ENV === "production" ? "; Secure" : ""
  }`;
}

export function buildOperatorSessionIdCookie(sessionId: string): string {
  return `${OPERATOR_SESSION_ID_COOKIE}=${encodeURIComponent(sessionId)}; Path=/; HttpOnly; SameSite=Strict${
    process.env.NODE_ENV === "production" ? "; Secure" : ""
  }`;
}

export function clearOperatorSessionCookie(): string {
  return `${OPERATOR_SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0`;
}

export function clearOperatorSessionIdCookie(): string {
  return `${OPERATOR_SESSION_ID_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0`;
}

export function validateOperatorToken(candidate: string | null | undefined): boolean {
  const token = getOperatorMutationToken();
  if (!token) {
    return process.env.NODE_ENV !== "production";
  }

  return candidate?.trim() === token;
}
