"use client";

import { motion } from "framer-motion";

interface QuickActionsProps {
  onAction: (action: string) => void;
  disabled?: boolean;
  sceneName: string;
}

/**
 * Quick action buttons for exploration scenes without characters.
 * Provides common actions that feed into the narration LLM.
 */
export function QuickActions({ onAction, disabled, sceneName }: QuickActionsProps) {
  const actions = [
    { label: "Look around", action: "*You look around, taking in your surroundings more carefully.*" },
    { label: "Listen", action: "*You stand still and listen to the sounds of the environment.*" },
    { label: "Search", action: "*You search the area for anything of interest.*" },
    { label: "Rest", action: "*You sit down for a moment to gather your thoughts.*" },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="fixed bottom-36 left-0 right-0 z-40 flex justify-center p-4"
      aria-label={`Quick actions for ${sceneName}`}
    >
      <div className="flex flex-wrap justify-center gap-2">
        {actions.map((a, i) => (
          <motion.button
            key={a.label}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            onClick={() => onAction(a.action)}
            disabled={disabled}
            className="rounded border border-white/15 bg-black/60 px-4 py-2 text-xs text-white/50 backdrop-blur-sm transition-colors hover:border-amber-400/30 hover:text-amber-400/60 disabled:opacity-30"
          >
            {a.label}
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
