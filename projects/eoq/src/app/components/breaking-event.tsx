"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";
import { getBreakingStage } from "@/types/game";

/**
 * Breaking stage change event — shows a dramatic notification
 * when a character crosses a breaking threshold.
 */

const STAGE_MESSAGES: Record<string, { title: string; desc: string; color: string }> = {
  struggling: {
    title: "Cracks Appearing",
    desc: "Their composure falters. Doubt creeps in.",
    color: "text-orange-400",
  },
  conflicted: {
    title: "Inner Conflict",
    desc: "Torn between resistance and surrender.",
    color: "text-yellow-400",
  },
  yielding: {
    title: "Resistance Fading",
    desc: "Their will bends under your influence.",
    color: "text-emerald-400",
  },
  surrendered: {
    title: "Will Broken",
    desc: "They exist to seek your approval.",
    color: "text-purple-400",
  },
  broken: {
    title: "Completely Broken",
    desc: "Total submission. They are yours.",
    color: "text-slate-400",
  },
};

export function BreakingEvent() {
  const session = useGameStore((s) => s.session);
  const [event, setEvent] = useState<{ charName: string; stage: string } | null>(null);
  const stagesRef = useRef<Record<string, string>>({});

  useEffect(() => {
    if (!session) return;

    for (const [charId, char] of Object.entries(session.characters)) {
      const stage = getBreakingStage(char.resistance);
      const prevStage = stagesRef.current[charId];

      if (prevStage && stage !== prevStage && STAGE_MESSAGES[stage]) {
        setEvent({ charName: char.name, stage });
        setTimeout(() => setEvent(null), 4000);
      }

      stagesRef.current[charId] = stage;
    }
  }, [session?.characters]);

  const msg = event ? STAGE_MESSAGES[event.stage] : null;

  return (
    <AnimatePresence>
      {event && msg && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={{ duration: 0.5 }}
          className="fixed inset-0 z-[90] flex items-center justify-center pointer-events-none"
        >
          <div className="rounded-lg border border-white/10 bg-black/90 px-8 py-6 text-center backdrop-blur-md">
            <p className={`text-xs uppercase tracking-widest ${msg.color}`}>
              {event.charName}
            </p>
            <h3 className={`mt-2 text-xl font-semibold tracking-wide ${msg.color}`}>
              {msg.title}
            </h3>
            <p className="mt-1 text-sm text-white/40">
              {msg.desc}
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
