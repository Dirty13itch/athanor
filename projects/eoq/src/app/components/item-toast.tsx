"use client";

import { useRef, useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";

const ITEM_NAMES: Record<string, string> = {
  truth_serum: "Truth Serum",
  blood_key: "Blood Key",
  kael_journal: "Kael's Journal",
  void_shard: "Void Shard",
  isolde_ring: "Isolde's Ring",
  oracle_fragment: "Oracle Fragment",
  tavern_key: "Tavern Key",
  fathers_letter: "Father's Letter",
};

export function ItemToast() {
  const session = useGameStore((s) => s.session);
  const [showing, setShowing] = useState<string | null>(null);
  const knownItemsRef = useRef<Set<string>>(new Set());
  const queueRef = useRef<string[]>([]);

  useEffect(() => {
    if (!session) {
      knownItemsRef.current = new Set();
      return;
    }

    const inventory = session.worldState.inventory;
    for (const item of inventory) {
      if (!knownItemsRef.current.has(item)) {
        knownItemsRef.current.add(item);
        queueRef.current.push(item);
      }
    }

    if (!showing && queueRef.current.length > 0) {
      const next = queueRef.current.shift()!;
      setShowing(next);
      setTimeout(() => setShowing(null), 3000);
    }
  }, [session, session?.worldState.inventory, showing]);

  return (
    <AnimatePresence>
      {showing && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="pointer-events-none fixed left-1/2 top-24 z-[90] -translate-x-1/2"
        >
          <div className="rounded border border-amber-400/30 bg-black/80 px-5 py-2.5 backdrop-blur-sm">
            <p className="text-[10px] uppercase tracking-widest text-amber-400/50">
              Item acquired
            </p>
            <p className="text-sm font-semibold text-amber-400">
              {ITEM_NAMES[showing] ?? showing}
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
