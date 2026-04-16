"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface SwipeCardProps {
  children: React.ReactNode;
  onSwipeRight?: () => void;
  onSwipeLeft?: () => void;
  rightLabel?: string;
  leftLabel?: string;
  rightColor?: string;
  leftColor?: string;
  threshold?: number;
  disabled?: boolean;
}

export function SwipeCard({
  children,
  onSwipeRight,
  onSwipeLeft,
  rightLabel = "Approve",
  leftLabel = "Reject",
  rightColor = "bg-green-500/20",
  leftColor = "bg-red-500/20",
  threshold = 0.3,
  disabled,
}: SwipeCardProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState(0);
  const [startX, setStartX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [containerWidth, setContainerWidth] = useState(300);

  useEffect(() => {
    if (!containerRef.current) return;

    const updateWidth = () => {
      setContainerWidth(containerRef.current?.offsetWidth ?? 300);
    };

    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, []);

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (disabled) return;
      setStartX(e.touches[0].clientX);
      setIsDragging(true);
    },
    [disabled]
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (!isDragging) return;
      const diff = e.touches[0].clientX - startX;
      const maxOffset = containerWidth * 0.5;
      setOffset(Math.max(-maxOffset, Math.min(maxOffset, diff)));
    },
    [containerWidth, isDragging, startX]
  );

  const handleTouchEnd = useCallback(() => {
    if (!isDragging) {
      setIsDragging(false);
      setOffset(0);
      return;
    }

    const ratio = Math.abs(offset) / containerWidth;

    if (ratio >= threshold) {
      if (offset > 0 && onSwipeRight) {
        onSwipeRight();
      } else if (offset < 0 && onSwipeLeft) {
        onSwipeLeft();
      }
    }

    setIsDragging(false);
    setOffset(0);
  }, [containerWidth, isDragging, offset, threshold, onSwipeRight, onSwipeLeft]);

  const ratio = Math.abs(offset) / containerWidth;
  const isRight = offset > 0;
  const showAction = ratio > 0.1;

  return (
    <div ref={containerRef} className="relative overflow-hidden rounded-lg">
      {/* Action reveal layer */}
      {showAction && (
        <div
          className={`absolute inset-0 flex items-center ${
            isRight ? `justify-start pl-4 ${rightColor}` : `justify-end pr-4 ${leftColor}`
          }`}
        >
          <span
            className="text-xs font-medium"
            style={{ opacity: Math.min(1, ratio * 3) }}
          >
            {isRight ? rightLabel : leftLabel}
          </span>
        </div>
      )}

      {/* Content layer */}
      <div
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        style={{
          transform: `translateX(${offset}px)`,
          transition: isDragging ? "none" : "transform 200ms ease-out",
        }}
        className="relative z-10"
      >
        {children}
      </div>
    </div>
  );
}
