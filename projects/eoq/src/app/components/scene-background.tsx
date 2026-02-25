"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useGameStore } from "@/stores/game-store";

export function SceneBackground() {
  const backgroundUrl = useGameStore((s) => s.backgroundUrl);
  const isGeneratingImage = useGameStore((s) => s.isGeneratingImage);

  return (
    <div className="fixed inset-0 z-0">
      <AnimatePresence mode="wait">
        {backgroundUrl ? (
          <motion.div
            key={backgroundUrl}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.0 }}
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: `url(${backgroundUrl})` }}
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-b from-slate-900 via-slate-800 to-slate-950" />
        )}
      </AnimatePresence>
      {isGeneratingImage && (
        <div className="absolute bottom-32 right-4 z-20 rounded bg-black/60 px-3 py-1 text-sm text-white/60">
          Generating scene...
        </div>
      )}
    </div>
  );
}
