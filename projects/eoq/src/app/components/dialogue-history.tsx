"use client";

import { useRef, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";
import { ProseText } from "./prose-text";
import { VoiceButton } from "./voice-button";

interface DialogueHistoryProps {
  open: boolean;
  onClose: () => void;
}

export function DialogueHistory({ open, onClose }: DialogueHistoryProps) {
  const session = useGameStore((s) => s.session);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState("");

  // Auto-scroll to bottom when opened (only if not searching)
  useEffect(() => {
    if (open && scrollRef.current && !search) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [open, search]);

  // Clear search when closing
  useEffect(() => {
    if (!open) setSearch("");
  }, [open]);

  if (!session) return null;

  const history = session.dialogueHistory;

  function getSpeakerName(speakerId: string): string {
    if (speakerId === "narrator") return "Narrator";
    if (speakerId === "player") return "You";
    const char = session?.characters[speakerId];
    return char?.name ?? speakerId;
  }

  function getSpeakerColor(speakerId: string): string {
    if (speakerId === "narrator") return "text-white/40";
    if (speakerId === "player") return "text-blue-400/80";
    return "text-amber-400/80";
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[55] flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            onClick={(e) => e.stopPropagation()}
            className="flex h-[70vh] w-full max-w-2xl flex-col rounded-lg border border-white/10 bg-slate-900/95"
          >
            {/* Header */}
            <div className="border-b border-white/10 p-4">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/70">
                  Dialogue History
                </h2>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-white/20">
                    {history.length} turns
                  </span>
                  <button
                    onClick={onClose}
                    className="text-xs text-white/30 transition-colors hover:text-white/60"
                  >
                    Close (H)
                  </button>
                </div>
              </div>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search dialogue..."
                className="w-full rounded border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/70 placeholder-white/20 focus:border-amber-400/30 focus:outline-none"
              />
            </div>

            {/* Scrollable history */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
              {(() => {
                const searchLower = search.toLowerCase();
                const filtered = search
                  ? history.filter(
                      (turn) =>
                        turn.text.toLowerCase().includes(searchLower) ||
                        getSpeakerName(turn.speaker).toLowerCase().includes(searchLower)
                    )
                  : history;
                if (filtered.length === 0) {
                  return (
                    <p className="text-center text-sm text-white/20 italic">
                      {search ? "No matches found." : "No dialogue yet."}
                    </p>
                  );
                }
                return (
                <div className="flex flex-col gap-3">
                  {filtered.map((turn, i) => (
                    <div key={i} className="group">
                      {turn.speaker !== "narrator" && (
                        <div className={`mb-0.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider ${getSpeakerColor(turn.speaker)}`}>
                          {getSpeakerName(turn.speaker)}
                          {turn.speaker !== "player" && (
                            <VoiceButton characterId={turn.speaker} text={turn.text} className="opacity-0 group-hover:opacity-100" />
                          )}
                        </div>
                      )}
                      {turn.speaker === "narrator" && (
                        <div className="mb-0.5 flex items-center gap-1.5">
                          <VoiceButton characterId="narrator" text={turn.text} className="opacity-0 group-hover:opacity-100" />
                        </div>
                      )}
                      <div
                        className={`text-sm leading-relaxed ${
                          turn.speaker === "narrator"
                            ? "text-white/40 italic"
                            : turn.speaker === "player"
                              ? "text-blue-200/70"
                              : "text-white/70"
                        }`}
                      >
                        <ProseText text={turn.text} />
                      </div>
                    </div>
                  ))}
                </div>
                );
              })()}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
