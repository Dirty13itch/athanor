"use client";

import { useState } from "react";

interface FeedbackButtonsProps {
  messageContent: string;
  agent?: string;
}

export function FeedbackButtons({ messageContent, agent }: FeedbackButtonsProps) {
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const [hidden, setHidden] = useState(false);

  async function handleFeedback(value: "up" | "down") {
    // Optimistic UI
    setFeedback(value);
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feedback_type: value === "up" ? "thumbs_up" : "thumbs_down",
          message_content: messageContent.substring(0, 500),
          agent: agent ?? "unknown",
        }),
      });
      // Hide buttons silently if endpoint doesn't exist
      if (res.status === 404 || res.status === 502) {
        setHidden(true);
      }
    } catch {
      // Silently ignore — feedback is best-effort
    }
  }

  if (hidden) return null;

  return (
    <div className="mt-1 flex items-center gap-1">
      <button
        onClick={() => handleFeedback("up")}
        className={`rounded p-1 text-xs transition-colors ${
          feedback === "up"
            ? "text-green-400"
            : "text-muted-foreground/40 hover:text-muted-foreground"
        }`}
        title="Good response"
      >
        <ThumbUpIcon className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={() => handleFeedback("down")}
        className={`rounded p-1 text-xs transition-colors ${
          feedback === "down"
            ? "text-red-400"
            : "text-muted-foreground/40 hover:text-muted-foreground"
        }`}
        title="Poor response"
      >
        <ThumbDownIcon className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function ThumbUpIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M7 10v12" />
      <path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" />
    </svg>
  );
}

function ThumbDownIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M17 14V2" />
      <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z" />
    </svg>
  );
}
