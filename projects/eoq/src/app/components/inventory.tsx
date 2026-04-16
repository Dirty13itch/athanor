"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";

interface InventoryProps {
  open: boolean;
  onClose: () => void;
}

/** Item descriptions for known items */
const ITEM_DESCRIPTIONS: Record<string, { name: string; desc: string; icon: string }> = {
  truth_serum: {
    name: "Truth Serum",
    desc: "A small vial from Mira. One dose — use it wisely.",
    icon: "🧪",
  },
  blood_key: {
    name: "Blood Key",
    desc: "An ancient key carved from dark crystal. It pulses with warmth.",
    icon: "🗝️",
  },
  kael_journal: {
    name: "Kael's Journal",
    desc: "Pages of cramped handwriting — history, regrets, and maps.",
    icon: "📓",
  },
  void_shard: {
    name: "Void Shard",
    desc: "A fragment of the Crimson Gate. Looking at it hurts.",
    icon: "💎",
  },
  isolde_ring: {
    name: "Isolde's Ring",
    desc: "A signet ring pressed into your hand when no one was looking.",
    icon: "💍",
  },
  oracle_fragment: {
    name: "Oracle Fragment",
    desc: "A piece of Seraphine's cracked orb. It shows glimpses of what's to come.",
    icon: "🔮",
  },
  tavern_key: {
    name: "Tavern Key",
    desc: "A key to the back room of The Broken Antler.",
    icon: "🔑",
  },
  fathers_letter: {
    name: "Father's Letter",
    desc: "A sealed letter bearing the royal crest. Kael won't open it.",
    icon: "✉️",
  },
};

export function Inventory({ open, onClose }: InventoryProps) {
  const session = useGameStore((s) => s.session);
  if (!session) return null;

  const items = session.worldState.inventory;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[65] flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-sm rounded-lg border border-white/10 bg-slate-900/95 p-5"
          >
            <h2 className="mb-4 text-center text-sm font-semibold uppercase tracking-wider text-amber-400/70">
              Inventory
            </h2>

            {items.length === 0 ? (
              <p className="py-8 text-center text-sm text-white/20 italic">
                You carry nothing of note.
              </p>
            ) : (
              <div className="flex flex-col gap-2">
                {items.map((itemId) => {
                  const info = ITEM_DESCRIPTIONS[itemId];
                  return (
                    <div
                      key={itemId}
                      className="flex items-start gap-3 rounded border border-white/5 bg-white/[0.02] p-3"
                    >
                      <span className="text-lg">{info?.icon ?? "📦"}</span>
                      <div>
                        <div className="text-xs font-medium text-white/70">
                          {info?.name ?? itemId}
                        </div>
                        <div className="text-[10px] text-white/30">
                          {info?.desc ?? "A mysterious item."}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <button
              onClick={onClose}
              className="mt-4 w-full rounded px-3 py-1.5 text-xs text-white/30 transition-colors hover:text-white/50"
            >
              Close
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
