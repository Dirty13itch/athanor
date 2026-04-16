import type { ChartPoint } from "@/lib/contracts";
import { cn } from "@/lib/utils";

function buildPath(points: ChartPoint[], width: number, height: number) {
  const numericPoints = points.filter((point) => point.value !== null);
  if (numericPoints.length === 0) {
    return "";
  }

  const min = Math.min(...numericPoints.map((point) => point.value as number));
  const max = Math.max(...numericPoints.map((point) => point.value as number));
  const range = max - min || 1;

  return numericPoints
    .map((point, index) => {
      const x = numericPoints.length === 1 ? width / 2 : (index / (numericPoints.length - 1)) * width;
      const y = height - (((point.value as number) - min) / range) * height;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

export function MiniTrend({
  points,
  className,
  strokeClassName,
}: {
  points: ChartPoint[];
  className?: string;
  strokeClassName?: string;
}) {
  const path = buildPath(points, 120, 36);

  return (
    <svg
      viewBox="0 0 120 36"
      className={cn("h-9 w-[7.5rem] text-primary/80", className)}
      aria-hidden="true"
    >
      <path
        d={path}
        fill="none"
        className={cn("stroke-current", strokeClassName)}
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
