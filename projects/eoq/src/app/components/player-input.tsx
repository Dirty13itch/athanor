"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";

interface PlayerInputProps {
  onSubmit: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

/**
 * Freeform text input for player dialogue.
 * Appears when there are no scripted choices and a character is present.
 * Enter submits, Shift+Enter for newline.
 */
export function PlayerInput({ onSubmit, disabled, placeholder }: PlayerInputProps) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus when not disabled
  useEffect(() => {
    if (!disabled && inputRef.current) {
      inputRef.current.focus();
    }
  }, [disabled]);

  function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setText("");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="fixed bottom-36 left-0 right-0 z-40 flex justify-center p-4"
    >
      <div className="flex w-full max-w-2xl gap-2">
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder ?? "What do you say?"}
          rows={1}
          className="flex-1 resize-none rounded border border-white/20 bg-black/70 px-4 py-3 text-sm text-white/90 placeholder-white/30 backdrop-blur-sm transition-colors focus:border-amber-400/50 focus:outline-none disabled:opacity-50"
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || !text.trim()}
          className="shrink-0 rounded border border-amber-400/30 bg-black/70 px-4 py-3 text-sm text-amber-400/80 backdrop-blur-sm transition-colors hover:border-amber-400/60 hover:bg-amber-900/30 disabled:opacity-30"
        >
          Send
        </button>
      </div>
    </motion.div>
  );
}
