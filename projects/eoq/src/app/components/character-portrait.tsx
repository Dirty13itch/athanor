"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useGameStore } from "@/stores/game-store";

function isVideoUrl(url: string): boolean {
  return /\.(mp4|webm|mov)(\?|$)/i.test(url);
}

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
          {isVideoUrl(portraitUrl) ? (
            <video
              src={portraitUrl}
              className="h-full w-auto object-contain drop-shadow-2xl rounded-lg"
              autoPlay
              loop
              muted
              playsInline
            />
          ) : (
            <img
              src={portraitUrl}
              alt="Character"
              className="h-full w-auto object-contain drop-shadow-2xl"
            />
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
