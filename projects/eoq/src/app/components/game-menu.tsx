"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import Link from "next/link";
import { useGameStore } from "@/stores/game-store";
import { KeyboardHelp } from "./keyboard-help";
import type { ContentIntensity } from "@/types/game";

interface GameMenuProps {
  open: boolean;
  onClose: () => void;
  onNewGame: () => void;
  onOpenInventory?: () => void;
}

const INTENSITY_LABELS: Record<ContentIntensity, { label: string; desc: string }> = {
  1: { label: "Mild", desc: "Romance and tension, fade-to-black" },
  2: { label: "Suggestive", desc: "Implied intimacy, sensual descriptions" },
  3: { label: "Mature", desc: "Explicit scenes, emotional depth" },
  4: { label: "Intense", desc: "Graphic content, power dynamics" },
  5: { label: "Extreme", desc: "No limits, full dark fantasy" },
};

function formatPlaytime(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

export function GameMenu({ open, onClose, onNewGame, onOpenInventory }: GameMenuProps) {
  const session = useGameStore((s) => s.session);
  const updateWorldState = useGameStore((s) => s.updateWorldState);
  const saveGame = useGameStore((s) => s.saveGame);
  const clearSave = useGameStore((s) => s.clearSave);

  const [showControls, setShowControls] = useState(false);
  const intensity = session?.worldState.contentIntensity ?? 3;

  function setIntensity(level: ContentIntensity) {
    updateWorldState({ contentIntensity: level });
    saveGame();
  }

  return (
    <>
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-sm rounded-lg border border-white/10 bg-slate-900/95 p-6"
          >
            <h2 className="mb-4 text-center text-lg font-semibold uppercase tracking-wider text-amber-400">
              Settings
            </h2>

            {/* Content intensity */}
            <div className="mb-6">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-white/40">
                Content Intensity
              </h3>
              <div className="flex flex-col gap-1.5">
                {([1, 2, 3, 4, 5] as ContentIntensity[]).map((level) => {
                  const info = INTENSITY_LABELS[level];
                  const active = level === intensity;
                  return (
                    <button
                      key={level}
                      onClick={() => setIntensity(level)}
                      className={`flex items-center gap-3 rounded border px-3 py-2 text-left text-sm transition-colors ${
                        active
                          ? "border-amber-400/40 bg-amber-900/20 text-amber-400"
                          : "border-white/5 bg-white/[0.02] text-white/50 hover:border-white/10 hover:text-white/70"
                      }`}
                    >
                      <span className="w-4 text-center text-xs font-bold">{level}</span>
                      <div>
                        <div className="font-medium">{info.label}</div>
                        <div className="text-[10px] text-white/30">{info.desc}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Game stats */}
            {session && (
              <div className="mb-6 rounded border border-white/5 bg-white/[0.02] p-3">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-white/40">
                  Session
                </h3>
                <div className="flex flex-col gap-1 text-xs text-white/30">
                  <div className="flex justify-between">
                    <span>Day</span>
                    <span className="text-white/50">{session.worldState.day}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Arc</span>
                    <span className="text-white/50">{session.arcPosition}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Dialogue turns</span>
                    <span className="text-white/50">{session.dialogueHistory.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Flags set</span>
                    <span className="text-white/50">
                      {Object.values(session.worldState.plotFlags).filter(Boolean).length}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Characters met</span>
                    <span className="text-white/50">
                      {[
                        session.worldState.plotFlags.met_isolde,
                        session.worldState.plotFlags.met_mira,
                        session.worldState.plotFlags.met_kael,
                        session.worldState.plotFlags.met_vaelis,
                        session.worldState.plotFlags.met_seraphine,
                      ].filter(Boolean).length}/5
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Playtime</span>
                    <span className="text-white/50">
                      {formatPlaytime(Date.now() - session.startedAt)}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-col gap-2">
              <button
                onClick={() => {
                  saveGame();
                  onClose();
                }}
                className="rounded border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/60 transition-colors hover:border-amber-400/30 hover:text-amber-400/60"
              >
                Save Game
              </button>
              <button
                onClick={() => {
                  if (confirm("Start a new game? Your current progress will be lost.")) {
                    clearSave();
                    onNewGame();
                    onClose();
                  }
                }}
                className="rounded border border-red-500/20 bg-red-900/10 px-4 py-2 text-sm text-red-400/60 transition-colors hover:border-red-500/30 hover:text-red-400/80"
              >
                New Game
              </button>
              {onOpenInventory && (
                <button
                  onClick={() => {
                    onClose();
                    onOpenInventory();
                  }}
                  className="rounded border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/60 transition-colors hover:border-amber-400/30 hover:text-amber-400/60"
                >
                  Inventory ({session?.worldState.inventory.length ?? 0})
                </button>
              )}
              <button
                onClick={() => setShowControls(true)}
                className="rounded border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/40 transition-colors hover:border-white/20 hover:text-white/60"
              >
                Controls
              </button>
              <Link
                href="/gallery"
                onClick={onClose}
                className="rounded border border-white/10 bg-white/5 px-4 py-2 text-center text-sm text-white/40 transition-colors hover:border-amber-400/30 hover:text-amber-400/60"
              >
                Portrait Gallery
              </Link>
              <button
                onClick={onClose}
                className="rounded px-4 py-2 text-sm text-white/30 transition-colors hover:text-white/50"
              >
                Close
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
    <KeyboardHelp open={showControls} onClose={() => setShowControls(false)} />
    </>
  );
}
