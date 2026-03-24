"use client";

import { useEffect, useRef, useCallback } from "react";

interface TouchControlsOptions {
  /** Called on swipe left (advance dialogue) */
  onSwipeLeft?: () => void;
  /** Called on swipe right (open history/log) */
  onSwipeRight?: () => void;
  /** Called on swipe up (open exits/map) */
  onSwipeUp?: () => void;
  /** Called on single tap (advance dialogue) */
  onTap?: () => void;
  /** Called on long press (open menu) */
  onLongPress?: () => void;
  /** Called on double tap (toggle auto-advance) */
  onDoubleTap?: () => void;
  /** Minimum swipe distance in px (default 50) */
  swipeThreshold?: number;
  /** Long press duration in ms (default 500) */
  longPressMs?: number;
  /** Whether controls are enabled */
  enabled?: boolean;
}

/**
 * Touch gesture controls for mobile VN experience.
 *
 * Gestures:
 * - Tap: advance dialogue
 * - Swipe left: advance dialogue
 * - Swipe right: open dialogue history
 * - Swipe up: open scene exits
 * - Long press (500ms): open game menu
 * - Double tap: toggle auto-advance
 *
 * Attach to the game container element.
 */
export function useTouchControls(
  ref: React.RefObject<HTMLElement | null>,
  options: TouchControlsOptions,
) {
  const {
    onSwipeLeft,
    onSwipeRight,
    onSwipeUp,
    onTap,
    onLongPress,
    onDoubleTap,
    swipeThreshold = 50,
    longPressMs = 500,
    enabled = true,
  } = options;

  const touchStart = useRef<{ x: number; y: number; time: number } | null>(null);
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastTapTime = useRef(0);
  const gestureHandled = useRef(false);

  const clearLongPress = useCallback(() => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el || !enabled) return;

    function handleTouchStart(e: TouchEvent) {
      if (e.touches.length !== 1) return;
      const touch = e.touches[0];
      touchStart.current = { x: touch.clientX, y: touch.clientY, time: Date.now() };
      gestureHandled.current = false;

      // Start long press timer
      longPressTimer.current = setTimeout(() => {
        gestureHandled.current = true;
        onLongPress?.();
        // Haptic feedback if available
        if (navigator.vibrate) navigator.vibrate(30);
      }, longPressMs);
    }

    function handleTouchMove(e: TouchEvent) {
      if (!touchStart.current || gestureHandled.current) return;
      const touch = e.touches[0];
      const dx = touch.clientX - touchStart.current.x;
      const dy = touch.clientY - touchStart.current.y;

      // If moved significantly, cancel long press
      if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
        clearLongPress();
      }
    }

    function handleTouchEnd(e: TouchEvent) {
      clearLongPress();
      if (!touchStart.current || gestureHandled.current) {
        touchStart.current = null;
        return;
      }

      const touch = e.changedTouches[0];
      const dx = touch.clientX - touchStart.current.x;
      const dy = touch.clientY - touchStart.current.y;
      const elapsed = Date.now() - touchStart.current.time;
      touchStart.current = null;

      const absDx = Math.abs(dx);
      const absDy = Math.abs(dy);

      // Swipe detection
      if (absDx > swipeThreshold || absDy > swipeThreshold) {
        if (absDx > absDy) {
          // Horizontal swipe
          if (dx < -swipeThreshold) {
            onSwipeLeft?.();
          } else if (dx > swipeThreshold) {
            onSwipeRight?.();
          }
        } else {
          // Vertical swipe
          if (dy < -swipeThreshold) {
            onSwipeUp?.();
          }
        }
        return;
      }

      // Tap detection (short touch, minimal movement)
      if (elapsed < 300 && absDx < 10 && absDy < 10) {
        const now = Date.now();
        if (now - lastTapTime.current < 300) {
          // Double tap
          onDoubleTap?.();
          lastTapTime.current = 0;
        } else {
          // Single tap (delayed to check for double)
          lastTapTime.current = now;
          setTimeout(() => {
            if (lastTapTime.current === now) {
              onTap?.();
            }
          }, 300);
        }
      }
    }

    // Don't intercept taps on interactive elements
    function shouldHandle(e: TouchEvent): boolean {
      const target = e.target as HTMLElement;
      if (!target) return true;
      const tag = target.tagName.toLowerCase();
      if (["button", "a", "input", "textarea", "select"].includes(tag)) return false;
      if (target.closest("button, a, input, textarea, [role='button']")) return false;
      return true;
    }

    function wrappedStart(e: TouchEvent) {
      if (shouldHandle(e)) handleTouchStart(e);
    }
    function wrappedMove(e: TouchEvent) {
      handleTouchMove(e);
    }
    function wrappedEnd(e: TouchEvent) {
      if (shouldHandle(e)) handleTouchEnd(e);
    }

    el.addEventListener("touchstart", wrappedStart, { passive: true });
    el.addEventListener("touchmove", wrappedMove, { passive: true });
    el.addEventListener("touchend", wrappedEnd, { passive: true });

    return () => {
      el.removeEventListener("touchstart", wrappedStart);
      el.removeEventListener("touchmove", wrappedMove);
      el.removeEventListener("touchend", wrappedEnd);
      clearLongPress();
    };
  }, [ref, enabled, onSwipeLeft, onSwipeRight, onSwipeUp, onTap, onLongPress, onDoubleTap, swipeThreshold, longPressMs, clearLongPress]);
}
