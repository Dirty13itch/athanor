"use client";

import { useState, useEffect, useRef } from "react";

/**
 * Typewriter effect hook — reveals text character by character.
 * When delayMs is 0, returns the full text immediately (for streaming mode).
 */
export function useTypewriter(text: string, delayMs: number = 20): string {
  const [displayed, setDisplayed] = useState("");
  const indexRef = useRef(0);

  useEffect(() => {
    if (delayMs === 0) {
      setDisplayed(text);
      return;
    }

    // Reset when text changes
    indexRef.current = 0;
    setDisplayed("");

    if (!text) return;

    const timer = setInterval(() => {
      indexRef.current += 1;
      if (indexRef.current >= text.length) {
        setDisplayed(text);
        clearInterval(timer);
      } else {
        setDisplayed(text.slice(0, indexRef.current));
      }
    }, delayMs);

    return () => clearInterval(timer);
  }, [text, delayMs]);

  return displayed;
}
