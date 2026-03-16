import { NextRequest, NextResponse } from "next/server";
import http from "node:http";

const DOCKER_SOCKET = "/var/run/docker.sock";

// Container names on Workshop
const VLLM_WORKER = "vllm-node2";
const COMFYUI = "comfyui";
const VLLM_VISION = "vllm-vision";

/** Make a request to the Docker Engine API via unix socket. */
function dockerApi(method: string, path: string, body?: unknown): Promise<{ status: number; data: unknown }> {
  return new Promise((resolve, reject) => {
    const options: http.RequestOptions = {
      socketPath: DOCKER_SOCKET,
      path,
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
    };
    const req = http.request(options, (res) => {
      const chunks: Buffer[] = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        const raw = Buffer.concat(chunks).toString();
        let data: unknown;
        try { data = JSON.parse(raw); } catch { data = raw; }
        resolve({ status: res.statusCode ?? 500, data });
      });
    });
    req.on("error", reject);
    req.setTimeout(10_000, () => { req.destroy(); reject(new Error("Docker API timeout")); });
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

async function isRunning(container: string): Promise<boolean> {
  try {
    const { status, data } = await dockerApi("GET", `/containers/${container}/json`);
    if (status !== 200) return false;
    return (data as { State?: { Running?: boolean } })?.State?.Running === true;
  } catch {
    return false;
  }
}

async function stopContainer(container: string): Promise<void> {
  await dockerApi("POST", `/containers/${container}/stop?t=10`);
}

async function startContainer(container: string): Promise<void> {
  await dockerApi("POST", `/containers/${container}/start`);
}

async function getStatus() {
  const [vllmUp, comfyUp, visionUp] = await Promise.all([
    isRunning(VLLM_WORKER),
    isRunning(COMFYUI),
    isRunning(VLLM_VISION),
  ]);

  let mode: string;
  if (vllmUp) mode = "inference";
  else if (comfyUp) mode = "creative";
  else mode = "idle";

  return {
    mode,
    gpu0: vllmUp ? "vLLM Worker (Qwen3.5-35B-A3B-AWQ)" : comfyUp ? "ComfyUI (Flux + PuLID)" : "idle",
    gpu1: visionUp ? "vLLM Vision (Qwen3-VL-8B, running)" : "vLLM Vision (stopped)",
    containers: { vllm_worker: vllmUp, comfyui: comfyUp, vision: visionUp },
  };
}

export async function GET() {
  try {
    const status = await getStatus();
    return NextResponse.json(status);
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

  if (mode !== "creative" && mode !== "inference") {
    return NextResponse.json(
      { error: `Invalid mode. Use 'creative' or 'inference'.` },
      { status: 400 },
    );
  }

  try {
    const steps: string[] = [];

    if (mode === "creative") {
      // Stop vLLM worker, start ComfyUI
      if (await isRunning(VLLM_WORKER)) {
        await stopContainer(VLLM_WORKER);
        steps.push("Stopped vLLM worker");
      }
      await startContainer(COMFYUI);
      steps.push("Started ComfyUI on GPU 0 (5090)");
    } else {
      // Stop ComfyUI, start vLLM worker
      if (await isRunning(COMFYUI)) {
        await stopContainer(COMFYUI);
        steps.push("Stopped ComfyUI");
      }
      await startContainer(VLLM_WORKER);
      steps.push("Started vLLM worker on GPU 0 (5090)");
    }

    const current = await getStatus();
    return NextResponse.json({ status: "ok", requested: mode, steps, current });
  } catch (err) {
    return NextResponse.json(
      { status: "error", error: err instanceof Error ? err.message : "GPU swap failed" },
      { status: 500 },
    );
  }
}
