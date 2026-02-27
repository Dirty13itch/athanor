"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";
import { FLAG_DESCRIPTIONS } from "@/data/narrative";

interface StoryJournalProps {
  open: boolean;
  onClose: () => void;
}

/** Group flags by category for display */
const FLAG_CATEGORIES: Record<string, { label: string; flags: string[] }> = {
  characters: {
    label: "Characters Met",
    flags: ["met_isolde", "met_mira", "met_kael", "met_vaelis", "met_seraphine"],
  },
  discoveries: {
    label: "Discoveries",
    flags: [
      "undercroft_unlocked",
      "crimson_gate_known",
      "knows_kael_is_prince",
      "kael_reveals_gate",
      "vaelis_grants_passage",
      "seraphine_invites_player",
      "vaelis_shared_truth",
      "mira_confession_heard",
      "seraphine_vision_seen",
    ],
  },
  decisions: {
    label: "Key Decisions",
    flags: [
      "isolde_proposal_heard",
      "chose_serve_isolde",
      "chose_defy_isolde",
      "isolde_ultimatum_faced",
      "mira_truth_serum_offered",
      "accepted_truth_serum",
      "rejected_truth_serum",
      "kael_gate_request",
      "kael_crisis_resolved",
      "kael_comforted",
      "kael_blood_key_known",
      "vaelis_request_heard",
      "saw_peaceful_future",
      "destroyed_mirrors",
    ],
  },
};

/**
 * Story journal overlay — tracks plot progress, discoveries, and key decisions.
 * Reads from plotFlags and shows human-readable descriptions from FLAG_DESCRIPTIONS.
 */
export function StoryJournal({ open, onClose }: StoryJournalProps) {
  const session = useGameStore((s) => s.session);
  const flags = session?.worldState.plotFlags ?? {};

  const setFlags = Object.entries(flags).filter(([, v]) => v);
  const totalKnownFlags = Object.keys(FLAG_DESCRIPTIONS).length;

  return (
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
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            onClick={(e) => e.stopPropagation()}
            className="max-h-[80vh] w-full max-w-md overflow-y-auto rounded-lg border border-white/10 bg-slate-900/95 p-5 backdrop-blur-sm"
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400">
                Story Journal
              </h2>
              <span className="text-[10px] text-white/20">
                {setFlags.length}/{totalKnownFlags} entries
              </span>
            </div>

            {/* Arc position */}
            {session && (
              <div className="mb-4 rounded border border-amber-400/20 bg-amber-900/10 px-3 py-2">
                <p className="text-[10px] uppercase tracking-wider text-amber-400/50">
                  Current Arc
                </p>
                <p className="text-sm text-amber-400/80">
                  {formatArcName(session.arcPosition)}
                </p>
              </div>
            )}

            {/* Categories */}
            {Object.entries(FLAG_CATEGORIES).map(([catId, category]) => {
              const discovered = category.flags.filter((f) => flags[f]);
              if (discovered.length === 0) return null;

              return (
                <div key={catId} className="mb-4">
                  <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-white/30">
                    {category.label}
                  </h3>
                  <div className="space-y-1">
                    {discovered.map((flagId) => (
                      <div
                        key={flagId}
                        className="flex items-start gap-2 rounded bg-white/[0.02] px-2.5 py-1.5"
                      >
                        <span className="mt-0.5 text-amber-400/40">&#9830;</span>
                        <p className="text-xs text-white/50">
                          {FLAG_DESCRIPTIONS[flagId] ?? flagId}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}

            {setFlags.length === 0 && (
              <p className="py-8 text-center text-sm text-white/20 italic">
                No entries yet. Explore Ashenmoor to uncover its secrets.
              </p>
            )}

            <button
              onClick={onClose}
              className="mt-2 w-full rounded border border-white/10 bg-white/5 px-4 py-2 text-xs text-white/40 transition-colors hover:text-white/60"
            >
              Close
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function formatArcName(arc: string): string {
  switch (arc) {
    case "prologue": return "Prologue — Arrival at Ashenmoor";
    case "gathering_allies": return "Gathering Allies";
    case "the_choice": return "The Choice";
    case "act1_end": return "Act 1 — Conclusion";
    default: return arc;
  }
}
