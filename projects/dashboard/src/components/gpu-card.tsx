import { Sparkline } from "./sparkline";

interface GpuCardProps {
  name: string;
  node: string;
  workload: string;
  utilization: number;
  temperature: number;
  power: number;
  powerLimit: number;
  memoryUsed: number;
  memoryTotal: number;
  sparklineData?: number[];
  compact?: boolean;
}

function utilColor(val: number): string {
  if (val > 80) return "text-red-400";
  if (val > 50) return "text-yellow-400";
  return "text-green-400";
}

function tempColor(val: number): string {
  if (val > 80) return "text-red-400";
  if (val > 65) return "text-yellow-400";
  return "text-green-400";
}

function formatMiB(mib: number): string {
  if (mib > 1024) return `${(mib / 1024).toFixed(1)} GB`;
  return `${mib.toFixed(0)} MB`;
}

export function GpuCard({
  name,
  workload,
  utilization,
  temperature,
  power,
  powerLimit,
  memoryUsed,
  memoryTotal,
  sparklineData,
  compact = false,
}: GpuCardProps) {
  const memPct = memoryTotal > 0 ? (memoryUsed / memoryTotal) * 100 : 0;

  if (compact) {
    return (
      <div className="rounded-md border border-border bg-card p-2 space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium truncate">{name}</span>
          <span className={`text-xs font-mono ${utilColor(utilization)}`}>{utilization.toFixed(0)}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full ${utilization > 80 ? "bg-red-500" : utilization > 50 ? "bg-yellow-500" : "bg-green-500"}`}
            style={{ width: `${Math.min(100, utilization)}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className={tempColor(temperature)}>{temperature.toFixed(0)}C</span>
          <span className="truncate ml-1">{workload}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">{name}</h3>
          <p className="text-xs text-muted-foreground">{workload}</p>
        </div>
        <span className={`text-lg font-mono font-semibold ${utilColor(utilization)}`}>
          {utilization.toFixed(0)}%
        </span>
      </div>

      {sparklineData && sparklineData.length > 1 && (
        <Sparkline
          data={sparklineData}
          width={200}
          height={32}
          color={utilization > 80 ? "#ef4444" : utilization > 50 ? "#eab308" : "#22c55e"}
          fill
          className="w-full"
        />
      )}

      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <span className="text-muted-foreground">Temp</span>
          <p className={`font-mono font-medium ${tempColor(temperature)}`}>{temperature.toFixed(0)}C</p>
        </div>
        <div>
          <span className="text-muted-foreground">Power</span>
          <p className="font-mono font-medium">{power.toFixed(0)}W / {powerLimit}W</p>
        </div>
        <div>
          <span className="text-muted-foreground">VRAM</span>
          <p className="font-mono font-medium">{formatMiB(memoryUsed)}</p>
        </div>
      </div>

      <div>
        <div className="flex justify-between text-xs text-muted-foreground mb-1">
          <span>VRAM</span>
          <span>{formatMiB(memoryUsed)} / {formatMiB(memoryTotal)}</span>
        </div>
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, memPct)}%` }} />
        </div>
      </div>
    </div>
  );
}
