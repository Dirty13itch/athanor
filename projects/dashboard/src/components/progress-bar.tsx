interface ProgressBarProps {
  value: number;
  max?: number;
  label?: string;
  showValue?: boolean;
  colorStops?: { threshold: number; color: string }[];
  className?: string;
}

const defaultColorStops = [
  { threshold: 80, color: "bg-red-500" },
  { threshold: 50, color: "bg-yellow-500" },
  { threshold: 0, color: "bg-green-500" },
];

export function ProgressBar({
  value,
  max = 100,
  label,
  showValue = false,
  colorStops = defaultColorStops,
  className,
}: ProgressBarProps) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const barColor = colorStops.find((s) => pct >= s.threshold)?.color ?? "bg-primary";

  return (
    <div className={className}>
      {(label || showValue) && (
        <div className="flex justify-between text-xs text-muted-foreground mb-1">
          {label && <span>{label}</span>}
          {showValue && <span>{pct.toFixed(0)}%</span>}
        </div>
      )}
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
