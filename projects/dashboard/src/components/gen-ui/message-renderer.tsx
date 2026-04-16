"use client";

import { CodeBlock } from "./code-block";

interface MessageRendererProps {
  content: string;
  role: "user" | "assistant";
}

interface Segment {
  type: "text" | "code";
  content: string;
  language?: string;
}

function parseSegments(text: string): Segment[] {
  const segments: Segment[] = [];
  // Split on fenced code blocks using string splitting approach
  const parts = text.split(/```(\w*)\n/);

  // parts alternates: text, lang, code-then-text, lang, code-then-text, ...
  // First part is always text before any code block
  for (let i = 0; i < parts.length; i++) {
    if (i === 0) {
      // Text before first code block
      if (parts[0].trim()) {
        segments.push({ type: "text", content: parts[0] });
      }
      continue;
    }

    // Odd indices are language captures
    if (i % 2 === 1) {
      const lang = parts[i] || undefined;
      const rest = parts[i + 1] ?? "";
      // Split on closing ```
      const closeIdx = rest.indexOf("```");
      if (closeIdx !== -1) {
        const code = rest.substring(0, closeIdx);
        const afterCode = rest.substring(closeIdx + 3);
        if (code) {
          segments.push({ type: "code", content: code, language: lang });
        }
        if (afterCode.trim()) {
          segments.push({ type: "text", content: afterCode });
        }
      } else {
        // Incomplete code block during streaming — treat as text
        if (rest.trim()) {
          segments.push({ type: "text", content: "```" + (lang ?? "") + "\n" + rest });
        }
      }
      i++; // Skip the next part (we consumed it)
    }
  }

  // If no segments were found, treat whole thing as text
  if (segments.length === 0 && text.trim()) {
    segments.push({ type: "text", content: text });
  }

  return segments;
}

export function MessageRenderer({ content, role }: MessageRendererProps) {
  if (role === "user") {
    return <>{content}</>;
  }

  const segments = parseSegments(content);

  if (segments.length === 1 && segments[0].type === "text") {
    return <>{content}</>;
  }

  return (
    <>
      {segments.map((seg, i) => {
        if (seg.type === "code") {
          return <CodeBlock key={i} code={seg.content} language={seg.language} />;
        }
        return (
          <span key={i} className="whitespace-pre-wrap">
            {seg.content}
          </span>
        );
      })}
    </>
  );
}
