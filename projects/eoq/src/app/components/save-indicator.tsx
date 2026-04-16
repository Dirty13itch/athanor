"use client";

import { useEffect, useState } from "react";
import { useGameStore } from "@/stores/game-store";

/**
 * Brief save indicator — flashes "Saved" when the game auto-saves.
 * Watches dialogue history length to detect save triggers.
 */
export function SaveIndicator() {
  const session = useGameStore((s) => s.session);
  const [showing, setShowing] = useState(false);
  const [lastLen, setLastLen] = useState(0);

  useEffect(() => {
    if (!session) return;
    const len = session.dialogueHistory.length;

    // Auto-save every 5 dialogue turns
    if (len > 0 && len !== lastLen && len % 5 === 0) {
      useGameStore.getState().saveGame();
      setShowing(true);
      setTimeout(() => setShowing(false), 1500);
    }
    setLastLen(len);
  }, [session, lastLen]);

  if (!showing) return null;

  return (
    <div className="fixed right-4 top-14 z-50 animate-pulse text-[10px] uppercase tracking-widest text-white/20">
      Saved
    </div>
  );
}
