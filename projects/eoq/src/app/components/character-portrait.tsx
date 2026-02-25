"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useGameStore } from "@/stores/game-store";

export function CharacterPortrait() {
  const portraitUrl = useGameStore((s) => s.portraitUrl);

  return (
    <AnimatePresence>
      {portraitUrl && (
        <motion.div
          key={portraitUrl}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.5 }}
          className="fixed bottom-48 right-8 z-10 h-[60vh] w-auto"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={portraitUrl}
            alt="Character"
            className="h-full w-auto object-contain drop-shadow-2xl"
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
