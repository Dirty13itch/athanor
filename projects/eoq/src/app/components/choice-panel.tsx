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
            className="group flex items-start gap-3 rounded border border-amber-400/30 bg-black/70 px-5 py-3 text-left text-white/90 backdrop-blur-sm transition-colors hover:border-amber-400/60 hover:bg-amber-900/30 disabled:opacity-50"
          >
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-white/10 text-[10px] font-semibold tabular-nums text-white/40 transition-colors group-hover:bg-amber-400/20 group-hover:text-amber-400/80">
              {i + 1}
            </span>
            <div className="flex flex-col">
              <span>{choice.text}</span>
              {(choice.intent || choice.breakingMethod) && (
                <span className="mt-0.5 text-[10px] text-white/20">
                  {choice.breakingMethod && (
                    <span className="mr-2 text-red-400/40">[{choice.breakingMethod}]</span>
                  )}
                  {choice.intent}
                </span>
              )}
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
