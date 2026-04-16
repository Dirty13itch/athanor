"use client";

import { useRef, useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";

const TIME_LABELS: Record<string, string> = {
  dawn: "Dawn breaks",
  morning: "Morning light",
  afternoon: "The sun climbs",
  dusk: "Twilight falls",
  evening: "Night descends",
  night: "Darkness reigns",
};

export function DayTransition() {
  const session = useGameStore((s) => s.session);
  const lastDayRef = useRef<number>(0);
  const [showing, setShowing] = useState<{ day: number; time: string } | null>(null);

  useEffect(() => {
    if (!session) {
      lastDayRef.current = 0;
      return;
    }

    const day = session.worldState.day;
    if (lastDayRef.current > 0 && day > lastDayRef.current) {
      setShowing({ day, time: session.worldState.timeOfDay });
      setTimeout(() => setShowing(null), 3500);
    }
    lastDayRef.current = day;
  }, [session, session?.worldState.day]);

  return (
    <AnimatePresence>
      {showing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1 }}
          className="pointer-events-none fixed inset-0 z-[75] flex items-center justify-center bg-black/40"
        >
          <div className="text-center">
            <motion.p
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="mb-2 text-[10px] uppercase tracking-[0.5em] text-white/30"
            >
              {TIME_LABELS[showing.time] ?? "Time passes"}
            </motion.p>
            <motion.h2
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5, duration: 0.6 }}
              className="text-5xl font-bold tracking-wider text-amber-400/80"
              style={{ textShadow: "0 0 40px oklch(0.80 0.12 85 / 0.3)" }}
            >
              Day {showing.day}
            </motion.h2>
            <motion.div
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ delay: 0.7, duration: 0.5 }}
              className="mx-auto mt-3 h-px w-32 bg-gradient-to-r from-transparent via-white/20 to-transparent"
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
