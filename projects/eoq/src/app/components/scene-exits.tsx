"use client";

import { motion } from "framer-motion";
import type { SceneExit } from "@/types/game";

interface SceneExitsProps {
  /** Exits that pass condition checks (player can use) */
  exits: SceneExit[];
  /** All exits on the scene (for showing locked paths) */
  allExits: SceneExit[];
  onExit: (exit: SceneExit) => void;
  onClose: () => void;
}

const CONDITION_HINTS: Record<string, string> = {
  undercroft_unlocked: "Earn Mira's trust",
  mira_trusts_player: "Mira must trust you",
  crimson_gate_known: "Learn about the Gate",
  kael_reveals_gate: "Kael must reveal the way",
  vaelis_grants_passage: "Earn Vaelis's respect",
  seraphine_invites_player: "Earn Seraphine's trust",
};

function getConditionHint(condition: string): string {
  return CONDITION_HINTS[condition] ?? "Requires further progress";
}

export function SceneExits({ exits, allExits, onExit, onClose }: SceneExitsProps) {
  const availableIds = new Set(exits.map((e) => e.targetSceneId));
  const lockedExits = allExits.filter((e) => !availableIds.has(e.targetSceneId));

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="fixed inset-x-0 top-14 z-30 flex justify-center p-4"
    >
      <div className="w-full max-w-md rounded-lg border border-white/10 bg-black/85 p-4 backdrop-blur-md">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-widest text-amber-400/70">
            Paths
          </h3>
          <button
            onClick={onClose}
            className="text-xs text-white/30 transition-colors hover:text-white/60"
          >
            Close
          </button>
        </div>

        <div className="flex flex-col gap-2">
          {exits.map((exit, i) => (
            <motion.button
              key={exit.targetSceneId}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => onExit(exit)}
              className="rounded border border-white/10 bg-white/5 px-4 py-2.5 text-left text-sm text-white/80 transition-colors hover:border-amber-400/30 hover:bg-amber-900/20 hover:text-amber-400/90"
            >
              {exit.label}
            </motion.button>
          ))}

          {lockedExits.map((exit) => (
            <div
              key={exit.targetSceneId}
              className="flex flex-col rounded border border-white/5 bg-white/[0.02] px-4 py-2.5"
            >
              <div className="flex items-center gap-2 text-sm text-white/20">
                <span className="text-[10px]">&#x1f512;</span>
                <span className="italic">{exit.label}</span>
              </div>
              {exit.condition && (
                <span className="ml-6 mt-0.5 text-[10px] text-white/10">
                  {getConditionHint(exit.condition)}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
