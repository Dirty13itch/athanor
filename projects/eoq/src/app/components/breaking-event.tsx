"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";
import { getBreakingStage } from "@/types/game";
import { getBreakingSequence } from "@/data/narrative";
import type { DialogueTurn } from "@/types/game";

/**
 * Breaking stage change event — shows dramatic cinematic sequences
 * when a character crosses a breaking threshold, with a title card overlay.
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

interface BreakingEventState {
  charName: string;
  charId: string;
  archetype: string;
  stage: string;
}

export function BreakingEvent() {
  const session = useGameStore((s) => s.session);
  const addDialogue = useGameStore((s) => s.addDialogue);
  const [event, setEvent] = useState<BreakingEventState | null>(null);
  const [sequencePlaying, setSequencePlaying] = useState(false);
  const [titleVisible, setTitleVisible] = useState(false);
  const stagesRef = useRef<Record<string, string>>({});

  const playSequence = useCallback((turns: DialogueTurn[]) => {
    setSequencePlaying(true);
    let index = 0;
    const playNext = () => {
      if (index >= turns.length) {
        setSequencePlaying(false);
        // Fade out title card after sequence
        setTimeout(() => setEvent(null), 2000);
        return;
      }
      addDialogue(turns[index]);
      index++;
      // Pause between turns for dramatic effect
      setTimeout(playNext, 2500);
    };
    // Start after title card has been visible for a moment
    setTimeout(playNext, 1500);
  }, [addDialogue]);

  useEffect(() => {
    if (!session) return;

    for (const [charId, char] of Object.entries(session.characters)) {
      const stage = getBreakingStage(char.resistance);
      const prevStage = stagesRef.current[charId];

      if (prevStage && stage !== prevStage && STAGE_MESSAGES[stage]) {
        const ev: BreakingEventState = {
          charName: char.name,
          charId,
          archetype: char.archetype,
          stage,
        };
        setEvent(ev);
        setTitleVisible(true);

        // Try to get a cinematic breaking sequence
        const sequence = getBreakingSequence(char.name, char.archetype, stage);
        if (sequence) {
          playSequence(sequence.turns);
        } else {
          // No sequence — just show the title card for 4 seconds
          setTimeout(() => setEvent(null), 4000);
        }
      }

      stagesRef.current[charId] = stage;
    }
  }, [session, playSequence]);

  const msg = event ? STAGE_MESSAGES[event.stage] : null;

  return (
    <AnimatePresence>
      {event && msg && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8 }}
          className="fixed inset-0 z-[90] flex items-center justify-center pointer-events-none"
        >
          {/* Dark vignette overlay during sequences */}
          {sequencePlaying && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black"
            />
          )}

          {/* Title card */}
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="relative rounded-lg border border-white/10 bg-black/95 px-10 py-8 text-center backdrop-blur-xl shadow-2xl"
          >
            {/* Decorative line */}
            <div className={`mx-auto mb-4 h-px w-16 ${msg.color.replace("text-", "bg-")} opacity-60`} />

            <p className={`text-xs uppercase tracking-[0.3em] ${msg.color} opacity-80`}>
              {event.charName}
            </p>
            <h3 className={`mt-3 text-2xl font-light tracking-wide ${msg.color}`}>
              {msg.title}
            </h3>
            <p className="mt-2 text-sm text-white/40 italic">
              {msg.desc}
            </p>

            {/* Decorative line */}
            <div className={`mx-auto mt-4 h-px w-16 ${msg.color.replace("text-", "bg-")} opacity-60`} />

            {sequencePlaying && (
              <p className="mt-4 text-xs text-white/20 animate-pulse">
                ...
              </p>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
