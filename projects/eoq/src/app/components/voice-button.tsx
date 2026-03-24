"use client";

import { useState, useRef, useCallback } from "react";
import { Volume2, Loader2, Square } from "lucide-react";

interface VoiceButtonProps {
  /** Character/speaker ID — "narrator", character id, or undefined */
  characterId?: string;
  /** The dialogue text to speak */
  text: string;
  /** Optional playback speed (0.5-2.0, default 1.0) */
  speed?: number;
  /** Optional extra CSS classes */
  className?: string;
}

/**
 * VoiceButton — click to hear a dialogue line spoken via Kokoro TTS.
 *
 * States: idle -> loading -> playing -> idle
 * Click while playing to stop. Click while idle to play.
 * Automatically stops any previously playing audio.
 */

// Module-level ref so only one voice plays at a time across all buttons
let activeAudio: HTMLAudioElement | null = null;
let activeCleanup: (() => void) | null = null;

function stopActiveAudio() {
  if (activeAudio) {
    activeAudio.pause();
    activeAudio.src = "";
  }
  if (activeCleanup) {
    activeCleanup();
    activeCleanup = null;
  }
  activeAudio = null;
}

export function VoiceButton({ characterId, text, speed, className }: VoiceButtonProps) {
  const [state, setState] = useState<"idle" | "loading" | "playing">("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleClick = useCallback(async () => {
    // If playing or loading, stop
    if (state === "playing" || state === "loading") {
      abortRef.current?.abort();
      stopActiveAudio();
      setState("idle");
      return;
    }

    // Don't speak empty text or player lines
    if (!text.trim() || characterId === "player") return;

    // Stop any other playing audio first
    stopActiveAudio();

    setState("loading");
    const abort = new AbortController();
    abortRef.current = abort;

    try {
      const res = await fetch("/api/voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          characterId: characterId ?? "narrator",
          text,
          speed: speed ?? 1.0,
        }),
        signal: abort.signal,
      });

      if (!res.ok || abort.signal.aborted) {
        setState("idle");
        return;
      }

      const blob = await res.blob();
      if (abort.signal.aborted) {
        setState("idle");
        return;
      }

      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      activeAudio = audio;

      const cleanup = () => {
        URL.revokeObjectURL(url);
        setState("idle");
        if (activeAudio === audio) {
          activeAudio = null;
          activeCleanup = null;
        }
      };
      activeCleanup = cleanup;

      audio.addEventListener("ended", cleanup);
      audio.addEventListener("error", cleanup);

      await audio.play();
      setState("playing");
    } catch {
      setState("idle");
    }
  }, [state, characterId, text, speed]);

  // Don't render for player lines
  if (characterId === "player") return null;

  const iconSize = 12;

  return (
    <button
      onClick={handleClick}
      disabled={state === "loading"}
      title={state === "playing" ? "Stop" : "Play voice"}
      className={`inline-flex items-center justify-center rounded p-1 transition-colors
        ${state === "playing"
          ? "text-amber-400 hover:text-amber-300"
          : state === "loading"
            ? "text-white/20 cursor-wait"
            : "text-white/20 hover:text-white/50"
        }
        ${className ?? ""}`}
    >
      {state === "loading" ? (
        <Loader2 size={iconSize} className="animate-spin" />
      ) : state === "playing" ? (
        <Square size={iconSize} />
      ) : (
        <Volume2 size={iconSize} />
      )}
    </button>
  );
}
