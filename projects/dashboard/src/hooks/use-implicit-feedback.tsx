"use client";

import { useEffect, useRef, useCallback } from "react";
import { usePathname } from "next/navigation";

interface ImplicitEvent {
  type: "page_view" | "dwell" | "tap" | "lens_change" | "scroll_depth";
  page: string;
  agent?: string;
  duration_ms?: number;
  metadata?: Record<string, unknown>;
  timestamp: number;
}

const BATCH_INTERVAL = 30_000; // 30 seconds
const MIN_DWELL_MS = 3_000; // Only log dwell > 3s

let eventQueue: ImplicitEvent[] = [];
let sessionId: string | null = null;

function getSessionId(): string {
  if (!sessionId) {
    sessionId = crypto.randomUUID();
  }
  return sessionId;
}

async function flushEvents() {
  if (eventQueue.length === 0) return;

  const batch = [...eventQueue];
  eventQueue = [];

  try {
    await fetch("/api/feedback/implicit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: getSessionId(),
        events: batch,
      }),
    });
  } catch {
    // Re-queue on failure (once only — don't accumulate)
    if (eventQueue.length === 0) {
      eventQueue = batch;
    }
  }
}

function pushEvent(event: ImplicitEvent) {
  eventQueue.push(event);
  // Auto-flush if queue gets large
  if (eventQueue.length >= 20) {
    flushEvents();
  }
}

export function useImplicitFeedback() {
  const pathname = usePathname();
  const pageEntryRef = useRef<number>(0);
  const lastPathRef = useRef<string>(pathname);

  // Track page views and dwell time
  useEffect(() => {
    const now = Date.now();

    // Log dwell time for previous page
    if (lastPathRef.current !== pathname) {
      const dwell = now - pageEntryRef.current;
      if (dwell >= MIN_DWELL_MS) {
        pushEvent({
          type: "dwell",
          page: lastPathRef.current,
          duration_ms: dwell,
          timestamp: now,
        });
      }
    }

    // Log page view for new page
    pushEvent({
      type: "page_view",
      page: pathname,
      timestamp: now,
    });

    pageEntryRef.current = now;
    lastPathRef.current = pathname;
  }, [pathname]);

  // Set up batch flush interval
  useEffect(() => {
    const interval = setInterval(flushEvents, BATCH_INTERVAL);

    // Flush on page unload
    const handleUnload = () => {
      const dwell = Date.now() - pageEntryRef.current;
      if (dwell >= MIN_DWELL_MS) {
        pushEvent({
          type: "dwell",
          page: lastPathRef.current,
          duration_ms: dwell,
          timestamp: Date.now(),
        });
      }
      // Use sendBeacon for reliable delivery during unload
      const data = JSON.stringify({
        session_id: getSessionId(),
        events: eventQueue,
      });
      navigator.sendBeacon("/api/feedback/implicit", data);
      eventQueue = [];
    };

    window.addEventListener("beforeunload", handleUnload);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        flushEvents();
      }
    });

    return () => {
      clearInterval(interval);
      window.removeEventListener("beforeunload", handleUnload);
      flushEvents();
    };
  }, []);

  // Track lens changes
  const trackLensChange = useCallback((from: string, to: string) => {
    pushEvent({
      type: "lens_change",
      page: lastPathRef.current,
      metadata: { from, to },
      timestamp: Date.now(),
    });
  }, []);

  // Track meaningful taps (agent interactions, etc.)
  const trackTap = useCallback((target: string, agent?: string) => {
    pushEvent({
      type: "tap",
      page: lastPathRef.current,
      agent,
      metadata: { target },
      timestamp: Date.now(),
    });
  }, []);

  return { trackLensChange, trackTap };
}
