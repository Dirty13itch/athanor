import { chatStreamEventSchema, type ChatStreamEvent } from "@/lib/contracts";

function parseEventBlock(block: string): string | null {
  const dataLines = block
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart());

  if (dataLines.length === 0) {
    return null;
  }

  return dataLines.join("\n");
}

function flushBufferedEvents(buffer: string, onEvent: (event: ChatStreamEvent) => void): string {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const eventBlocks = normalized.split("\n\n");
  const remainder = eventBlocks.pop() ?? "";

  for (const block of eventBlocks) {
    const data = parseEventBlock(block);
    if (!data || data === "[DONE]") {
      continue;
    }

    try {
      const parsed = chatStreamEventSchema.parse(JSON.parse(data));
      onEvent(parsed);
    } catch {
      // Ignore malformed or unrelated SSE chunks.
    }
  }

  return remainder;
}

export async function readChatEventStream(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: ChatStreamEvent) => void
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    buffer = flushBufferedEvents(buffer, onEvent);
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    flushBufferedEvents(`${buffer}\n\n`, onEvent);
  }
}

export function toSseEvent(event: ChatStreamEvent): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}
