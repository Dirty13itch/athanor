"use client";

import { useState, useRef, useCallback } from "react";

interface VoiceOutputProps {
  messageContent: string;
}

export function VoiceOutput({ messageContent }: VoiceOutputProps) {
  const [state, setState] = useState<"idle" | "loading" | "playing">("idle");
  const [hidden, setHidden] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);

  const cleanup = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
  }, []);

  const handleClick = useCallback(async () => {
    if (state === "playing") {
      cleanup();
      setState("idle");
      return;
    }

    if (state === "loading") return;

    // Strip markdown code blocks and excessive whitespace for cleaner TTS
    const text = messageContent
      .replace(/```[\s\S]*?```/g, "")
      .replace(/`[^`]+`/g, (m) => m.slice(1, -1))
      .replace(/\n{3,}/g, "\n\n")
      .trim();

    if (!text) return;

    setState("loading");
    try {
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: text }),
      });

      if (res.status === 404 || res.status === 502) {
        setHidden(true);
        setState("idle");
        return;
      }

      if (!res.ok) {
        setState("idle");
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      urlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => {
        cleanup();
        setState("idle");
      };

      audio.onerror = () => {
        cleanup();
        setState("idle");
      };

      await audio.play();
      setState("playing");
    } catch {
      cleanup();
      setState("idle");
    }
  }, [state, messageContent, cleanup]);

  if (hidden) return null;

  return (
    <button
      onClick={handleClick}
      disabled={state === "loading"}
      className={`rounded p-1 text-xs transition-colors ${
        state === "playing"
          ? "text-primary"
          : state === "loading"
            ? "text-muted-foreground/40 animate-pulse"
            : "text-muted-foreground/40 hover:text-muted-foreground"
      }`}
      title={
        state === "playing" ? "Stop" : state === "loading" ? "Generating speech..." : "Read aloud"
      }
    >
      {state === "playing" ? (
        <StopIcon className="h-3.5 w-3.5" />
      ) : (
        <SpeakerIcon className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

function SpeakerIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    </svg>
  );
}

function StopIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}
