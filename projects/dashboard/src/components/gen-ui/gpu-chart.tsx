"use client";

import type { GpuMetricParsed } from "@/lib/generative-ui";

function barColor(value: number): string {
  if (value >= 80) return "oklch(0.65 0.2 25)"; // red
  if (value >= 50) return "oklch(0.75 0.15 85)"; // yellow
  return "oklch(0.65 0.18 145)"; // green
}

export function GpuChart({ metrics }: { metrics: GpuMetricParsed[] }) {
  const barHeight = 18;
  const labelWidth = 80;
  const barMaxWidth = 140;
  const gap = 4;
  const totalHeight = metrics.length * (barHeight + gap);

  return (
    <svg
      viewBox={`0 0 ${labelWidth + barMaxWidth + 40} ${totalHeight}`}
      className="w-full max-w-sm"
      style={{ height: Math.max(totalHeight, 40) }}
    >
      {metrics.map((m, i) => {
        const y = i * (barHeight + gap);
        const width = (m.value / 100) * barMaxWidth;
        return (
          <g key={i}>
            <text
              x={labelWidth - 4}
              y={y + barHeight / 2 + 1}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-current text-muted-foreground"
              fontSize="10"
            >
              {m.label}
            </text>
            <rect
              x={labelWidth}
              y={y}
              width={barMaxWidth}
              height={barHeight}
              rx="3"
              fill="oklch(0.18 0.005 60)"
            />
            <rect
              x={labelWidth}
              y={y}
              width={Math.max(width, 2)}
              height={barHeight}
              rx="3"
              fill={barColor(m.value)}
            />
            <text
              x={labelWidth + barMaxWidth + 4}
              y={y + barHeight / 2 + 1}
              dominantBaseline="middle"
              className="fill-current text-foreground"
              fontSize="10"
              fontFamily="var(--font-geist-mono)"
            >
              {m.value}%
            </text>
          </g>
        );
      })}
    </svg>
  );
}
