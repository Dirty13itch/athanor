"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";

/**
 * Toast notification for newly unlocked areas/flags.
 * Watches plot flags and shows a brief notification when new ones appear.
 */

const UNLOCK_MESSAGES: Record<string, string> = {
  undercroft_unlocked: "The Undercroft is now accessible from the courtyard",
  mira_trusts_player: "Mira trusts you enough to share her secrets",
  crimson_gate_known: "You've learned about the Crimson Gate",
  kael_reveals_gate: "Kael has told you about the tunnel to the Gate",
  vaelis_grants_passage: "Vaelis grants you passage beyond the Gate",
  seraphine_invites_player: "Seraphine invites you into the Vision Chamber",
};

export function UnlockToast() {
  const session = useGameStore((s) => s.session);
  const [toast, setToast] = useState<string | null>(null);
  const knownFlagsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!session) return;

    const currentFlags = Object.entries(session.worldState.plotFlags)
      .filter(([, v]) => v)
      .map(([k]) => k);

    for (const flag of currentFlags) {
      if (!knownFlagsRef.current.has(flag) && UNLOCK_MESSAGES[flag]) {
        setToast(UNLOCK_MESSAGES[flag]);
        setTimeout(() => setToast(null), 3500);
      }
    }

    knownFlagsRef.current = new Set(currentFlags);
  }, [session?.worldState.plotFlags]);

  return (
    <AnimatePresence>
      {toast && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.4 }}
          className="fixed left-1/2 top-24 z-50 -translate-x-1/2 rounded-lg border border-amber-400/30 bg-black/80 px-5 py-3 backdrop-blur-sm"
        >
          <p className="text-center text-sm text-amber-400/80">
            {toast}
          </p>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
