"use client";

import { useMemo } from "react";

/**
 * Renders game text with markdown-like formatting.
 * Supports *italic* (action text) and **bold** (emphasis).
 * Preserves whitespace and newlines.
 */
export function ProseText({ text, className }: { text: string; className?: string }) {
  const segments = useMemo(() => parseProseText(text), [text]);

  return (
    <span className={className}>
      {segments.map((seg, i) => {
        switch (seg.type) {
          case "bold":
            return (
              <strong key={i} className="font-semibold text-white">
                {seg.text}
              </strong>
            );
          case "italic":
            return (
              <em key={i} className="italic text-white/60">
                {seg.text}
              </em>
            );
          default:
            return <span key={i}>{seg.text}</span>;
        }
      })}
    </span>
  );
}

interface TextSegment {
  type: "text" | "bold" | "italic";
  text: string;
}

function parseProseText(text: string): TextSegment[] {
  const segments: TextSegment[] = [];
  // Match **bold** and *italic* — bold must be checked first
  const regex = /(\*\*(.+?)\*\*)|(\*(.+?)\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    // Push preceding text
    if (match.index > lastIndex) {
      segments.push({ type: "text", text: text.slice(lastIndex, match.index) });
    }

    if (match[2]) {
      // **bold**
      segments.push({ type: "bold", text: match[2] });
    } else if (match[4]) {
      // *italic*
      segments.push({ type: "italic", text: match[4] });
    }

    lastIndex = match.index + match[0].length;
  }

  // Push remaining text
  if (lastIndex < text.length) {
    segments.push({ type: "text", text: text.slice(lastIndex) });
  }

  return segments;
}
