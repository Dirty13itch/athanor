"use client";

import { useEffect, useRef } from "react";

interface AutoAdvanceProps {
  active: boolean;
  onToggle: () => void;
  onAdvance: () => void;
  canAdvance: boolean;
  hasChoices: boolean;
  isGenerating: boolean;
}

/**
 * Auto-advance indicator + timer.
 * When active and no choices pending, auto-advances after a delay.
 * Pauses when choices appear or during generation.
 */
export function AutoAdvance({
  active,
  onToggle,
  onAdvance,
  canAdvance,
  hasChoices,
  isGenerating,
}: AutoAdvanceProps) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    if (active && canAdvance && !hasChoices && !isGenerating) {
      timerRef.current = setTimeout(() => {
        onAdvance();
      }, 3000);
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [active, canAdvance, hasChoices, isGenerating, onAdvance]);

  return (
    <button
      onClick={onToggle}
      className={`fixed bottom-4 right-4 z-40 rounded border px-2 py-1 text-[10px] uppercase tracking-wider transition-all ${
        active
          ? "border-amber-400/30 bg-amber-900/20 text-amber-400/60"
          : "border-white/10 bg-black/40 text-white/20 hover:text-white/40"
      }`}
      title="Toggle auto-advance (A)"
    >
      {active ? "Auto ▶" : "Auto ⏸"}
    </button>
  );
}
