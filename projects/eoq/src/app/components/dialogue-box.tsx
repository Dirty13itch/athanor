"use client";

import { useRef, useEffect } from "react";
import { useGameStore } from "@/stores/game-store";
import { useTypewriter } from "./use-typewriter";
import { ProseText } from "./prose-text";
import { getBreakingStage } from "@/types/game";

export function DialogueBox() {
  const { session, streamingText, isGenerating } = useGameStore();
  const boxRef = useRef<HTMLDivElement>(null);
  const history = session?.dialogueHistory ?? [];
  const lastTurn = history[history.length - 1];

  // Use streaming text if generating, otherwise show the last completed turn.
  // delayMs=0 always — streaming provides the animation, no need to re-typewriter.
  const displayText = isGenerating ? streamingText : (lastTurn?.text ?? "");
  const speakerId = isGenerating ? "..." : (lastTurn?.speaker ?? "");
  const animatedText = useTypewriter(displayText, 0);

  // Resolve character name, emotion, and title from session
  let speakerLabel = speakerId;
  let emotionLabel: string | null = null;
  let charTitle: string | null = null;
  let breakingStage: string | null = null;
  if (speakerId && speakerId !== "narrator" && speakerId !== "player" && speakerId !== "..." && session) {
    const char = session.characters[speakerId];
    if (char) {
      speakerLabel = char.name;
      charTitle = char.title ?? null;
      breakingStage = getBreakingStage(char.resistance);
      if (char.emotion.primary && char.emotion.intensity > 0.2) {
        emotionLabel = char.emotion.primary;
      }
    }
  }

  // Auto-scroll to bottom when streaming new text
  useEffect(() => {
    if (boxRef.current && isGenerating) {
      boxRef.current.scrollTop = boxRef.current.scrollHeight;
    }
  }, [animatedText, isGenerating]);

  // Breaking stage color for the speaker name
  const stageNameColor = breakingStage ? stageAccent(breakingStage) : "";

  if (!displayText && !isGenerating) return null;

  // Show shimmer when generating but no text yet (waiting for first token)
  const showShimmer = isGenerating && !streamingText;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-30 p-4">
      <div ref={boxRef} className={`mx-auto max-w-4xl max-h-[40vh] overflow-y-auto rounded-t-lg bg-black/80 p-6 backdrop-blur-sm border border-white/10 ${showShimmer ? "shimmer" : ""}`}>
        {speakerLabel && speakerLabel !== "narrator" && speakerLabel !== "player" && speakerLabel !== "..." && (
          <div className="mb-2">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold uppercase tracking-wider ${stageNameColor || "text-amber-400"}`}>
                {speakerLabel}
              </span>
              {charTitle && (
                <span className="text-[10px] text-white/20">
                  {charTitle}
                </span>
              )}
              {emotionLabel && (
                <span className={`text-[10px] uppercase tracking-wider ${emotionColor(emotionLabel)}`}>
                  · {emotionLabel}
                </span>
              )}
            </div>
          </div>
        )}
        {speakerLabel === "narrator" && (
          <div className="mb-2">
            <span className="text-[10px] uppercase tracking-widest text-white/20">
              &#x2756; Narrator
            </span>
          </div>
        )}
        <div className={`text-lg leading-relaxed whitespace-pre-wrap ${
          speakerLabel === "narrator" ? "text-white/60 italic" :
          speakerLabel === "player" ? "text-blue-200/80" :
          "text-white/90"
        }`}>
          {showShimmer ? (
            <span className="text-white/20 italic">
              <span className="inline-block animate-pulse">...</span>
            </span>
          ) : (
            <>
              <ProseText text={animatedText} />
              {isGenerating && (
                <span className="ml-1 inline-block animate-pulse text-amber-400">
                  |
                </span>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/** Map emotion labels to tailwind text colors */
function emotionColor(emotion: string): string {
  const map: Record<string, string> = {
    angry: "text-red-400/50",
    fearful: "text-purple-400/50",
    aroused: "text-rose-400/50",
    sad: "text-blue-400/50",
    contemptuous: "text-orange-400/50",
    amused: "text-emerald-400/50",
    curious: "text-cyan-400/50",
    tender: "text-pink-400/50",
    defiant: "text-red-400/50",
    vulnerable: "text-violet-400/50",
    calculating: "text-amber-400/50",
    stoic: "text-slate-300/50",
    playful: "text-yellow-400/50",
    melancholic: "text-indigo-400/50",
    anxious: "text-orange-300/50",
    intense: "text-rose-500/50",
    guilty: "text-purple-300/50",
    distressed: "text-red-300/50",
    afraid: "text-violet-300/50",
    desperate: "text-amber-300/50",
    excited: "text-emerald-300/50",
    resigned: "text-slate-400/50",
    conflicted: "text-yellow-300/50",
    devastated: "text-blue-300/50",
    exhausted: "text-slate-300/50",
    hopeful: "text-cyan-300/50",
    serious: "text-white/40",
    broken: "text-slate-500/50",
  };
  return map[emotion.toLowerCase()] ?? "text-white/25";
}

/** Map breaking stage to speaker name color accent */
function stageAccent(stage: string): string {
  switch (stage) {
    case "defiant": return "text-amber-400";
    case "struggling": return "text-amber-300";
    case "conflicted": return "text-yellow-400";
    case "yielding": return "text-emerald-400";
    case "surrendered": return "text-purple-400";
    case "broken": return "text-slate-400";
    default: return "";
  }
}
