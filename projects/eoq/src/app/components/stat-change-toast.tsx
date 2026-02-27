"use client";

import { useRef, useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";
import type { Character } from "@/types/game";

interface StatDiff {
  label: string;
  value: number;
  color: string;
}

/**
 * Brief floating indicators showing relationship stat changes after choices.
 * Compares current character stats with a snapshot taken before each choice.
 */
export function StatChangeToast() {
  const session = useGameStore((s) => s.session);
  const [diffs, setDiffs] = useState<StatDiff[]>([]);
  const prevCharsRef = useRef<Record<string, Character> | null>(null);
  const prevInventoryRef = useRef<string[]>([]);
  const turnCountRef = useRef(0);

  useEffect(() => {
    if (!session) {
      prevCharsRef.current = null;
      turnCountRef.current = 0;
      return;
    }

    const currentTurnCount = session.dialogueHistory.length;
    if (currentTurnCount <= turnCountRef.current) {
      turnCountRef.current = currentTurnCount;
      prevCharsRef.current = structuredClone(session.characters);
      prevInventoryRef.current = [...session.worldState.inventory];
      return;
    }

    // Check if the new turn was a player turn (means a choice was just made)
    const lastTurn = session.dialogueHistory[session.dialogueHistory.length - 1];
    if (lastTurn?.speaker !== "player" || !prevCharsRef.current) {
      turnCountRef.current = currentTurnCount;
      prevCharsRef.current = structuredClone(session.characters);
      prevInventoryRef.current = [...session.worldState.inventory];
      return;
    }

    const changes: StatDiff[] = [];
    const presentChars = session.worldState.currentScene.presentCharacters;

    for (const charId of presentChars) {
      const prev = prevCharsRef.current[charId];
      const curr = session.characters[charId];
      if (!prev || !curr) continue;

      const statChecks: Array<{ key: "trust" | "affection" | "respect" | "desire" | "fear"; label: string; color: string }> = [
        { key: "trust", label: "Trust", color: "text-blue-400" },
        { key: "affection", label: "Affection", color: "text-pink-400" },
        { key: "respect", label: "Respect", color: "text-amber-400" },
        { key: "desire", label: "Desire", color: "text-rose-400" },
        { key: "fear", label: "Fear", color: "text-purple-400" },
      ];

      for (const stat of statChecks) {
        const diff = (curr.relationship[stat.key] as number) - (prev.relationship[stat.key] as number);
        if (diff !== 0) {
          changes.push({ label: stat.label, value: diff, color: stat.color });
        }
      }

      const resDiff = curr.resistance - prev.resistance;
      if (resDiff !== 0) {
        changes.push({ label: "Resistance", value: resDiff, color: "text-red-400" });
      }

      const corDiff = curr.corruption - prev.corruption;
      if (corDiff !== 0) {
        changes.push({ label: "Corruption", value: corDiff, color: "text-purple-400" });
      }
    }

    if (changes.length > 0) {
      setDiffs(changes);
      setTimeout(() => setDiffs([]), 2500);
    }

    turnCountRef.current = currentTurnCount;
    prevCharsRef.current = structuredClone(session.characters);
    prevInventoryRef.current = [...session.worldState.inventory];
  }, [session, session?.dialogueHistory.length]);

  return (
    <AnimatePresence>
      {diffs.length > 0 && (
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="pointer-events-none fixed bottom-48 left-4 z-50 flex flex-col gap-1"
        >
          {diffs.map((d, i) => (
            <motion.div
              key={`${d.label}-${i}`}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`text-xs font-semibold ${d.color}`}
            >
              {d.value > 0 ? "+" : ""}{d.value} {d.label}
            </motion.div>
          ))}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
