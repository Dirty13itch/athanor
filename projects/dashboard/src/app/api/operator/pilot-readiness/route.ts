import { NextResponse } from "next/server";
import { loadCapabilityPilotReadiness } from "@/lib/capability-pilot-readiness";

export async function GET() {
  try {
    return NextResponse.json(await loadCapabilityPilotReadiness());
  } catch (error) {
    return NextResponse.json(
      {
        generatedAt: new Date().toISOString(),
        available: false,
        degraded: true,
        detail: `Failed to load capability pilot readiness: ${error instanceof Error ? error.message : "unknown error"}`,
        sourceKind: null,
        sourcePath: null,
        summary: {
          total: 0,
          formalEvalComplete: 0,
          formalEvalFailed: 0,
          manualReviewPending: 0,
          readyForFormalEval: 0,
          operatorSmokeOnly: 0,
          scaffoldOnly: 0,
          blocked: 0,
        },
        records: [],
      },
      { status: 200 },
    );
  }
}
