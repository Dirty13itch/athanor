"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";
import { generateNews, type NewsItem } from "@/data/news";

/**
 * Empire News Network — ambient news ticker that reflects game state.
 * Shows one headline at a time, cycling through relevant news.
 * Appears at the top of the game screen as atmospheric flavor.
 */
export function EmpireNews() {
  const session = useGameStore((s) => s.session);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (!session) return;
    const items = generateNews(session);
    setNews(items);
    setCurrentIndex(0);
  }, [
    session?.arcPosition,
    session?.worldState.plotFlags,
    session?.playerStyle.totalChoices,
  ]);

  // Cycle through headlines
  useEffect(() => {
    if (news.length <= 1) return;
    const timer = setInterval(() => {
      setCurrentIndex((i) => (i + 1) % news.length);
    }, 12000); // 12 seconds per headline
    return () => clearInterval(timer);
  }, [news.length]);

  if (news.length === 0 || !visible) return null;

  const current = news[currentIndex];
  if (!current) return null;

  const toneColors: Record<string, string> = {
    neutral: "text-white/40",
    ominous: "text-red-400/60",
    hopeful: "text-emerald-400/60",
    fearful: "text-amber-400/60",
    propagandist: "text-purple-400/60",
  };

  return (
    <div className="fixed top-0 left-0 right-0 z-[40] pointer-events-none">
      <div className="pointer-events-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.6 }}
            className="flex items-center justify-between bg-black/60 backdrop-blur-sm px-4 py-1.5 border-b border-white/5"
          >
            <div className="flex items-center gap-3 min-w-0">
              <span className={`text-[9px] font-bold uppercase tracking-[0.2em] shrink-0 ${toneColors[current.tone] ?? "text-white/40"}`}>
                {current.source}
              </span>
              <span className="text-[11px] text-white/50 truncate">
                {current.headline}
              </span>
            </div>
            <button
              onClick={() => setVisible(false)}
              className="shrink-0 ml-2 text-[10px] text-white/20 hover:text-white/40"
            >
              x
            </button>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
