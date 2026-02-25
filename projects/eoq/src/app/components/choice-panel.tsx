"use client";

import { motion } from "framer-motion";
import type { PlayerChoice } from "@/types/game";

interface ChoicePanelProps {
  choices: PlayerChoice[];
  onChoose: (choice: PlayerChoice) => void;
  disabled?: boolean;
}

export function ChoicePanel({ choices, onChoose, disabled }: ChoicePanelProps) {
  if (choices.length === 0) return null;

  return (
    <div className="fixed bottom-36 left-0 right-0 z-40 flex justify-center p-4">
      <div className="flex max-w-2xl flex-col gap-3">
        {choices.map((choice, i) => (
          <motion.button
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            onClick={() => onChoose(choice)}
            disabled={disabled}
            className="rounded border border-amber-400/30 bg-black/70 px-6 py-3 text-left text-white/90 backdrop-blur-sm transition-colors hover:border-amber-400/60 hover:bg-amber-900/30 disabled:opacity-50"
          >
            {choice.text}
          </motion.button>
        ))}
      </div>
    </div>
  );
}
