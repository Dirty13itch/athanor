import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import {
  type OperatorActionRequest,
  operatorActionRequestSchema,
  operatorAuthClassSchema,
} from "@/lib/contracts";
import {
  agentServerHeaders,
  config,
  joinUrl,
} from "@/lib/config";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";
import {
  getOperatorMutationToken,
  hasValidOperatorSession,
  getOperatorSessionId,
  requireSameOriginOperatorSessionAccess,
} from "@/lib/operator-auth";
import { proxyAgentJson } from "@/lib/server-agent";

export type OperatorAuthClass = "read-only" | "operator" | "admin" | "destructive-admin";

type OperatorActionOptions = {
  privilegeClass: OperatorAuthClass;
  defaultActor?: string;
  defaultReason?: string;
  bodyOverride?: ParsedMutationBody;
};

type OperatorAuditEvent = {
  service: string;
  route: string;
  action_class: OperatorAuthClass;
  decision: "accepted" | "denied";
  status_code: number;
  detail?: string | null;
  target?: string | null;
  metadata?: Record<string, unknown>;
  action: OperatorActionRequest;
};

type ParsedMutationBody = Record<string, unknown>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function coerceBoolean(value: unknown): boolean {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string") {
    return /^(1|true|yes|on)$/i.test(value.trim());
  }
  if (typeof value === "number") {
    return value !== 0;
  }
  return false;
}

function coerceString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function resolveOperatorEnvelopeSessionId(request: Request, body: ParsedMutationBody): string {
  const explicitSessionId = coerceString(body.session_id);
  if (explicitSessionId) {
    return explicitSessionId;
  }

  const cookieSessionId = getOperatorSessionId(request);
  if (cookieSessionId) {
    return cookieSessionId;
  }

  const configuredToken = getOperatorMutationToken();
  if (!configuredToken || !hasValidOperatorSession(request)) {
    return "";
  }

  return `dashboard-session-${randomUUID()}`;
}

async function parseMutationBody(request: NextRequest): Promise<ParsedMutationBody | NextResponse> {
  const contentType = request.headers.get("content-type")?.toLowerCase() ?? "";
  if (!contentType.includes("application/json")) {
    return {};
  }

  const body = await request.json().catch(() => null);
  if (body === null) {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }
  if (!isRecord(body)) {
    return NextResponse.json({ error: "JSON body must be an object" }, { status: 400 });
  }
  return body;
}

export function buildOperatorActionRequest(
  request: Request,
  body: ParsedMutationBody,
  options: OperatorActionOptions
): { action: OperatorActionRequest; payload: ParsedMutationBody } | NextResponse {
  const action = operatorActionRequestSchema.safeParse({
    actor: coerceString(body.actor) || options.defaultActor || "dashboard-operator",
    session_id: resolveOperatorEnvelopeSessionId(request, body),
    correlation_id: coerceString(body.correlation_id) || randomUUID(),
    reason: coerceString(body.reason) || options.defaultReason || "",
    dry_run: coerceBoolean(body.dry_run),
    protected_mode: coerceBoolean(body.protected_mode),
  });

  if (!action.success) {
    return NextResponse.json(
      {
        error: "Operator action envelope is required",
        issues: action.error.flatten().fieldErrors,
      },
      { status: 400 }
    );
  }

  if (
    (options.privilegeClass === "admin" || options.privilegeClass === "destructive-admin") &&
    !action.data.reason.trim()
  ) {
    return NextResponse.json(
      {
        error: "reason is required for admin and destructive-admin actions",
        action_class: options.privilegeClass,
      },
      { status: 400 }
    );
  }

  if (options.privilegeClass === "destructive-admin" && !action.data.protected_mode) {
    return NextResponse.json(
      {
        error: "protected_mode=true is required for destructive-admin actions",
        action_class: options.privilegeClass,
      },
      { status: 400 }
    );
  }

  return {
    action: action.data,
    payload: {
      ...body,
      ...action.data,
    },
  };
}

export async function proxyAgentOperatorJson(
  request: NextRequest,
  path: string,
  errorMessage: string,
  options: OperatorActionOptions & { timeoutMs?: number }
) {
  const gate = requireSameOriginOperatorSessionAccess(request);
  if (gate) {
    return gate;
  }

  const parsedBody = options.bodyOverride ?? (await parseMutationBody(request));
  if (parsedBody instanceof NextResponse) {
    return parsedBody;
  }

  const prepared = buildOperatorActionRequest(request, parsedBody, options);
  if (prepared instanceof NextResponse) {
    return prepared;
  }

  return proxyAgentJson(
    path,
    {
      method: request.method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(prepared.payload),
    },
    errorMessage,
    options.timeoutMs
  );
}

export async function emitOperatorAuditEvent(event: OperatorAuditEvent): Promise<void> {
  if (isDashboardFixtureMode()) {
    return;
  }

  try {
    await fetch(joinUrl(config.agentServer.url, "/v1/operator/audit"), {
      method: "POST",
      headers: {
        ...agentServerHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(event),
      signal: AbortSignal.timeout(5_000),
    });
  } catch {
    // Best-effort audit forwarding. Do not break the operator flow on audit transport failure.
  }
}
