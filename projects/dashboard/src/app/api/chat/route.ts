import { NextRequest } from "next/server";
import { z } from "zod";
import { joinUrl, resolveChatTarget } from "@/lib/config";
import { toSseEvent } from "@/lib/sse";

const chatRequestSchema = z.object({
  messages: z.array(
    z.object({
      role: z.enum(["system", "user", "assistant"]),
      content: z.string(),
    })
  ),
  model: z.string().optional(),
  target: z.string().optional(),
  threadId: z.string().optional(),
});

function parseEventBlock(block: string) {
  let eventName: string | null = null;
  const dataLines = block
    .split("\n")
    .map((line) => {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      }
      return line;
    })
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart());

  if (!dataLines.length) {
    return null;
  }

  return {
    eventName,
    data: dataLines.join("\n"),
  };
}

function normalizePayload(payload: unknown, eventName?: string | null) {
  const timestamp = new Date().toISOString();
  if (typeof payload !== "object" || payload === null) {
    return [];
  }

  const record = payload as Record<string, unknown>;
  const eventType = typeof record.type === "string" ? record.type : eventName;

  if (eventType === "tool_start" && typeof record.name === "string") {
    return [
      toSseEvent({
        type: "tool_start",
        timestamp,
        toolCallId:
          typeof record.toolCallId === "string"
            ? record.toolCallId
            : typeof record.run_id === "string"
              ? record.run_id
              : `${record.name}-${Date.now()}`,
        name: record.name,
        args:
          typeof record.args === "object" && record.args !== null
            ? (record.args as Record<string, unknown>)
            : undefined,
      }),
    ];
  }

  if (eventType === "tool_end" && typeof record.name === "string") {
    return [
      toSseEvent({
        type: "tool_end",
        timestamp,
        toolCallId:
          typeof record.toolCallId === "string"
            ? record.toolCallId
            : typeof record.run_id === "string"
              ? record.run_id
              : `${record.name}-${Date.now()}`,
        name: record.name,
        output:
          typeof record.output === "string"
            ? record.output
            : typeof record.result === "string"
              ? record.result
              : undefined,
        durationMs: typeof record.durationMs === "number"
          ? record.durationMs
          : typeof record.duration_ms === "number"
            ? record.duration_ms
            : undefined,
        error: typeof record.error === "string" ? record.error : undefined,
      }),
    ];
  }

  const choices = Array.isArray(record.choices) ? record.choices : [];
  const firstChoice =
    choices[0] && typeof choices[0] === "object" ? (choices[0] as Record<string, unknown>) : null;
  const delta =
    firstChoice?.delta && typeof firstChoice.delta === "object"
      ? (firstChoice.delta as Record<string, unknown>)
      : null;

  const events: string[] = [];
  if (typeof delta?.content === "string" && delta.content.length > 0) {
    events.push(
      toSseEvent({
        type: "assistant_delta",
        timestamp,
        content: delta.content,
      })
    );
  }

  if (typeof firstChoice?.finish_reason === "string" && firstChoice.finish_reason.length > 0) {
    events.push(
      toSseEvent({
        type: "done",
        timestamp,
        finishReason: firstChoice.finish_reason,
      })
    );
  }

  return events;
}

export async function POST(req: NextRequest) {
  const parseResult = chatRequestSchema.safeParse(await req.json());
  if (!parseResult.success) {
    return new Response("Invalid request", { status: 400 });
  }

  const { messages, model, target, threadId } = parseResult.data;

  const resolvedTarget = resolveChatTarget(target);
  if (!resolvedTarget) {
    return new Response("Unknown chat target", { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(joinUrl(resolvedTarget.url, "/v1/chat/completions"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({
        model: model ?? "default",
        messages,
        max_tokens: 2048,
        temperature: 0.7,
        stream: true,
        ...(target === "agent-server" && threadId ? { thread_id: threadId } : {}),
      }),
    });
  } catch {
    return new Response("Unable to reach upstream chat backend", { status: 502 });
  }

  if (!upstream.ok) {
    const text = await upstream.text();
    return new Response(text, { status: upstream.status });
  }

  if (!upstream.body) {
    return new Response("Missing upstream stream body", { status: 502 });
  }

  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  const normalizedStream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const reader = upstream.body!.getReader();
      let buffer = "";
      let emittedDone = false;

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const normalized = buffer.replace(/\r\n/g, "\n");
          const blocks = normalized.split("\n\n");
          buffer = blocks.pop() ?? "";

          for (const block of blocks) {
            const parsed = parseEventBlock(block);
            if (!parsed) {
              continue;
            }

            if (parsed.data === "[DONE]") {
              if (!emittedDone) {
                controller.enqueue(
                  encoder.encode(
                    toSseEvent({
                      type: "done",
                      timestamp: new Date().toISOString(),
                      finishReason: "stop",
                    })
                  )
                );
                emittedDone = true;
              }
              continue;
            }

            try {
              const payload = JSON.parse(parsed.data);
              for (const event of normalizePayload(payload, parsed.eventName)) {
                if (event.includes('"type":"done"')) {
                  emittedDone = true;
                }
                controller.enqueue(encoder.encode(event));
              }
            } catch {
              // Ignore malformed upstream chunks.
            }
          }
        }

        if (buffer.trim()) {
          const parsed = parseEventBlock(`${buffer}\n\n`);
          if (parsed && parsed.data !== "[DONE]") {
            try {
              const payload = JSON.parse(parsed.data);
              for (const event of normalizePayload(payload, parsed.eventName)) {
                if (event.includes('"type":"done"')) {
                  emittedDone = true;
                }
                controller.enqueue(encoder.encode(event));
              }
            } catch {
              // Ignore malformed final chunk.
            }
          }
        }

        if (!emittedDone) {
          controller.enqueue(
            encoder.encode(
              toSseEvent({
                type: "done",
                timestamp: new Date().toISOString(),
                finishReason: "stop",
              })
            )
          );
        }
      } catch (error) {
        controller.enqueue(
          encoder.encode(
            toSseEvent({
              type: "error",
              timestamp: new Date().toISOString(),
              message:
                error instanceof Error ? error.message : "Failed to normalize upstream stream",
            })
          )
        );
      } finally {
        controller.close();
      }
    },
  });

  return new Response(normalizedStream, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
