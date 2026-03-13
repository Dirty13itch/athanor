import { NextRequest, NextResponse } from "next/server";

const FIXTURE_SESSION_COOKIE = "athanor_fixture_session";

export function proxy(request: NextRequest) {
  if (process.env.DASHBOARD_FIXTURE_MODE !== "1") {
    return NextResponse.next();
  }

  if (request.cookies.get(FIXTURE_SESSION_COOKIE)?.value) {
    return NextResponse.next();
  }

  const response = NextResponse.next();
  response.cookies.set(FIXTURE_SESSION_COOKIE, crypto.randomUUID(), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
  });
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
