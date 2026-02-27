"use client";

import { useRef, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";

const ARCHETYPE_LABELS: Record<string, string> = {
  warrior: "The Warrior",
  sorceress: "The Sorceress",
  priestess: "The Priestess",
  scholar: "The Scholar",
  merchant: "The Merchant",
  innocent: "The Innocent",
  defiant: "The Defiant",
  seductress: "The Seductress",
  ice: "The Ice Queen",
  fire: "The Fire",
  shadow: "The Shadow",
  sun: "The Sun",
};

interface IntroData {
  name: string;
  title: string;
  archetype: string;
}

export function CharacterIntro() {
  const session = useGameStore((s) => s.session);
  const [showing, setShowing] = useState<IntroData | null>(null);
  const knownCharsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!session) {
      knownCharsRef.current = new Set();
      return;
    }

    const flags = session.worldState.plotFlags;
    const metFlags = ["met_isolde", "met_mira", "met_kael", "met_vaelis", "met_seraphine"];

    for (const flag of metFlags) {
      if (flags[flag] && !knownCharsRef.current.has(flag)) {
        knownCharsRef.current.add(flag);
        const charId = flag.replace("met_", "");
        const char = session.characters[charId];
        if (char) {
          setShowing({
            name: char.name,
            title: char.title ?? "",
            archetype: ARCHETYPE_LABELS[char.archetype] ?? char.archetype,
          });
          setTimeout(() => setShowing(null), 4000);
        }
      }
    }
  }, [session, session?.worldState.plotFlags]);

  return (
    <AnimatePresence>
      {showing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8 }}
          className="pointer-events-none fixed inset-0 z-[80] flex items-center justify-center"
        >
          <div className="text-center">
            <motion.div
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              className="mx-auto mb-4 h-px w-48 bg-gradient-to-r from-transparent via-amber-400/60 to-transparent"
            />
            <motion.h2
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="mb-1 text-3xl font-bold tracking-wider text-amber-400"
              style={{ textShadow: "0 0 30px oklch(0.80 0.12 85 / 0.4)" }}
            >
              {showing.name}
            </motion.h2>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.5 }}
              className="mb-1 text-sm tracking-widest text-white/50"
            >
              {showing.title}
            </motion.p>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8, duration: 0.5 }}
              className="text-[10px] uppercase tracking-[0.3em] text-white/25"
            >
              {showing.archetype}
            </motion.p>
            <motion.div
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ delay: 0.4, duration: 0.6, ease: "easeOut" }}
              className="mx-auto mt-4 h-px w-48 bg-gradient-to-r from-transparent via-amber-400/60 to-transparent"
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
