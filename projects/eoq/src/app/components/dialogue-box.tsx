"use client";

import { useGameStore } from "@/stores/game-store";
import { useTypewriter } from "./use-typewriter";

export function DialogueBox() {
  const { session, streamingText, isGenerating } = useGameStore();
  const history = session?.dialogueHistory ?? [];
  const lastTurn = history[history.length - 1];

  // Use streaming text if generating, otherwise show the last completed turn.
  // delayMs=0 always — streaming provides the animation, no need to re-typewriter.
  const displayText = isGenerating ? streamingText : (lastTurn?.text ?? "");
  const speaker = isGenerating ? "..." : (lastTurn?.speaker ?? "");
  const animatedText = useTypewriter(displayText, 0);

  if (!displayText && !isGenerating) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-30 p-4">
      <div className="mx-auto max-w-4xl rounded-t-lg bg-black/80 p-6 backdrop-blur-sm border border-white/10">
        {speaker && speaker !== "narrator" && (
          <div className="mb-2 text-sm font-semibold uppercase tracking-wider text-amber-400">
            {speaker}
          </div>
        )}
        <div className="text-lg leading-relaxed text-white/90">
          {animatedText}
          {isGenerating && (
            <span className="ml-1 inline-block animate-pulse text-amber-400">
              |
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
