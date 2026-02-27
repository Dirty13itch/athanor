"use client";

import { motion, AnimatePresence } from "framer-motion";

interface KeyboardHelpProps {
  open: boolean;
  onClose: () => void;
}

const CONTROLS = [
  { key: "Space / Enter", desc: "Advance dialogue" },
  { key: "1-9", desc: "Select a choice" },
  { key: "E", desc: "Toggle exploration menu" },
  { key: "H", desc: "Toggle dialogue history" },
  { key: "I", desc: "Toggle character info" },
  { key: "M", desc: "Toggle scene map" },
  { key: "A", desc: "Toggle auto-advance" },
  { key: "Esc", desc: "Close menus / Open settings" },
  { key: "Shift+Enter", desc: "Newline in text input" },
];

export function KeyboardHelp({ open, onClose }: KeyboardHelpProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-xs rounded-lg border border-white/10 bg-slate-900/95 p-5"
          >
            <h2 className="mb-4 text-center text-sm font-semibold uppercase tracking-wider text-amber-400/70">
              Controls
            </h2>
            <div className="flex flex-col gap-2">
              {CONTROLS.map((c) => (
                <div key={c.key} className="flex items-center justify-between">
                  <kbd className="rounded bg-white/5 px-2 py-0.5 text-[10px] font-mono text-amber-400/60">
                    {c.key}
                  </kbd>
                  <span className="text-xs text-white/40">{c.desc}</span>
                </div>
              ))}
            </div>
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
