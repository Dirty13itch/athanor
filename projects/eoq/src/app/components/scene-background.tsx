"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useGameStore } from "@/stores/game-store";

/** Time-of-day gradient backgrounds — atmospheric fallbacks when no ComfyUI image */
const TIME_GRADIENTS: Record<string, string> = {
  dawn: "from-indigo-950 via-purple-900/80 to-orange-950/60",
  morning: "from-slate-800 via-blue-900/60 to-amber-950/40",
  afternoon: "from-slate-700 via-slate-800/80 to-amber-950/50",
  dusk: "from-slate-900 via-red-950/60 to-orange-950/40",
  evening: "from-slate-950 via-indigo-950/70 to-slate-900",
  night: "from-slate-950 via-slate-900 to-slate-950",
};

export function SceneBackground() {
  const backgroundUrl = useGameStore((s) => s.backgroundUrl);
  const isGeneratingImage = useGameStore((s) => s.isGeneratingImage);
  const session = useGameStore((s) => s.session);

  const timeOfDay = session?.worldState.timeOfDay ?? "night";
  const gradient = TIME_GRADIENTS[timeOfDay] ?? TIME_GRADIENTS.night;

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
          <motion.div
            key={timeOfDay}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2.0 }}
            className={`absolute inset-0 bg-gradient-to-b ${gradient}`}
          />
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
