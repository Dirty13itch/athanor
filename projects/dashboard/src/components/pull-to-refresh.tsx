"use client";

import { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";

interface PullToRefreshProps {
  children: React.ReactNode;
}

const THRESHOLD = 80;
const MAX_PULL = 120;

export function PullToRefresh({ children }: PullToRefreshProps) {
  const router = useRouter();
  const [pullDistance, setPullDistance] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const startY = useRef(0);
  const pulling = useRef(false);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    // Only activate when scrolled to top
    const target = e.currentTarget;
    if (target.scrollTop > 0) return;
    startY.current = e.touches[0].clientY;
    pulling.current = true;
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!pulling.current || refreshing) return;
    const delta = e.touches[0].clientY - startY.current;
    if (delta < 0) {
      pulling.current = false;
      setPullDistance(0);
      return;
    }
    // Dampen pull distance
    const distance = Math.min(delta * 0.5, MAX_PULL);
    setPullDistance(distance);
  }, [refreshing]);

  const handleTouchEnd = useCallback(() => {
    if (!pulling.current) return;
    pulling.current = false;

    if (pullDistance >= THRESHOLD && !refreshing) {
      setRefreshing(true);
      setPullDistance(THRESHOLD * 0.5);
      router.refresh();
      // Reset after a short delay to let server component re-render
      setTimeout(() => {
        setRefreshing(false);
        setPullDistance(0);
      }, 1000);
    } else {
      setPullDistance(0);
    }
  }, [pullDistance, refreshing, router]);

  return (
    <div
      className="relative h-full overflow-auto"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Pull indicator */}
      <div
        className="flex items-center justify-center overflow-hidden transition-[height] duration-200"
        style={{ height: pullDistance > 0 ? pullDistance : 0 }}
      >
        <div
          className={`text-xs text-muted-foreground transition-opacity ${
            refreshing ? "animate-pulse" : pullDistance >= THRESHOLD ? "opacity-100" : "opacity-50"
          }`}
        >
          {refreshing ? "Refreshing..." : pullDistance >= THRESHOLD ? "Release to refresh" : "Pull to refresh"}
        </div>
      </div>
      {children}
    </div>
  );
}
