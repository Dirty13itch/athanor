import { describe, expect, it } from "vitest";
import { readChatEventStream, toSseEvent } from "./sse";

function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();

  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

describe("readChatEventStream", () => {
  it("parses normalized events split across chunks", async () => {
    const events: unknown[] = [];

    await readChatEventStream(
      makeStream([
        'data: {"type":"assistant_delta","time',
        'stamp":"2026-03-09T00:00:00.000Z","content":"Hel"}\n\n',
        'data: {"type":"assistant_delta","timestamp":"2026-03-09T00:00:01.000Z","content":"lo"}\n\n',
        'data: {"type":"done","timestamp":"2026-03-09T00:00:02.000Z","finishReason":"stop"}\n\n',
      ]),
      (event) => events.push(event)
    );

    expect(events).toHaveLength(3);
    expect(events[0]).toMatchObject({ type: "assistant_delta", content: "Hel" });
    expect(events[1]).toMatchObject({ type: "assistant_delta", content: "lo" });
    expect(events[2]).toMatchObject({ type: "done", finishReason: "stop" });
  });

  it("serializes normalized events back to SSE", () => {
    const payload = toSseEvent({
      type: "tool_start",
      timestamp: "2026-03-09T00:00:00.000Z",
      toolCallId: "tool-123",
      name: "check_services",
      args: { node: "node1" },
    });

    expect(payload).toContain('"type":"tool_start"');
    expect(payload).toContain('"toolCallId":"tool-123"');
  });
});
