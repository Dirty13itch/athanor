import { NextRequest, NextResponse } from "next/server";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const GPU_SWAP_SCRIPT = "/opt/athanor/gpu-swap.sh";
const VALID_MODES = new Set(["creative", "inference", "status"]);

export async function GET() {
  try {
    const { stdout } = await execFileAsync(GPU_SWAP_SCRIPT, ["status"], {
      timeout: 10_000,
    });
    const lines = stdout.trim().split("\n");
    const modeLine = lines.find((l) => l.startsWith("MODE:"));
    const mode = modeLine?.split(":")[1]?.trim() ?? "unknown";
    return NextResponse.json({ mode, detail: lines });
  } catch (err) {
    return NextResponse.json(
      { mode: "unknown", error: err instanceof Error ? err.message : "Failed to get GPU status" },
      { status: 500 },
    );
  }
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  const mode = (body as Record<string, unknown>).mode;

  if (typeof mode !== "string" || !VALID_MODES.has(mode) || mode === "status") {
    return NextResponse.json(
      { error: `Invalid mode. Use 'creative' or 'inference'.` },
      { status: 400 },
    );
  }

  try {
    const { stdout } = await execFileAsync(GPU_SWAP_SCRIPT, [mode], {
      timeout: 300_000, // 5 min — vLLM cold start takes ~90s
    });
    return NextResponse.json({ status: "ok", mode, output: stdout.trim() });
  } catch (err) {
    return NextResponse.json(
      { status: "error", error: err instanceof Error ? err.message : "GPU swap failed" },
      { status: 500 },
    );
  }
}
