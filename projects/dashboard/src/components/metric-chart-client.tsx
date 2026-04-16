"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatNumber, formatTimestamp } from "@/lib/format";

interface SeriesDefinition {
  dataKey: string;
  label: string;
  color: string;
}

export function MetricChartClient({
  data,
  series,
  mode = "line",
  valueSuffix = "",
}: {
  data: Array<Record<string, number | string | null>>;
  series: SeriesDefinition[];
  mode?: "line" | "area";
  valueSuffix?: string;
}) {
  const ChartComponent = mode === "area" ? AreaChart : LineChart;

  return (
    <div className="h-64 min-h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ChartComponent data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--line-soft)" strokeOpacity={0.55} vertical={false} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(value) =>
              new Date(value).toLocaleTimeString([], {
                hour: "numeric",
                minute: "2-digit",
              })
            }
            stroke="var(--text-muted)"
            minTickGap={24}
          />
          <YAxis
            stroke="var(--text-muted)"
            tickFormatter={(value: number) => formatNumber(value, 0)}
            width={42}
          />
          <Tooltip
            content={({ active, payload, label }) => (
              <TooltipContent
                active={Boolean(active)}
                payload={payload as unknown as ReadonlyArray<{
                  name?: string;
                  value?: unknown;
                  color?: string;
                }> | undefined}
                label={label}
                valueSuffix={valueSuffix}
              />
            )}
          />
          {series.map((item) =>
            mode === "area" ? (
              <Area
                key={item.dataKey}
                type="monotone"
                dataKey={item.dataKey}
                name={item.label}
                stroke={item.color}
                fill={item.color}
                fillOpacity={0.16}
                strokeWidth={2}
                connectNulls
              />
            ) : (
              <Line
                key={item.dataKey}
                type="monotone"
                dataKey={item.dataKey}
                name={item.label}
                stroke={item.color}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            )
          )}
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  );
}

function TooltipContent({
  active,
  payload,
  label,
  valueSuffix,
}: {
  active: boolean;
  payload?: ReadonlyArray<{ name?: string; value?: unknown; color?: string }>;
  label?: unknown;
  valueSuffix: string;
}) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div className="surface-chrome rounded-2xl border p-3 shadow-2xl">
      <p className="mb-2 text-xs text-muted-foreground">{formatTimestamp(String(label ?? ""))}</p>
      <div className="space-y-1.5">
        {payload.map((entry) => (
          <div key={`${entry.name}`} className="flex items-center justify-between gap-4 text-xs">
            <span className="flex items-center gap-2 text-muted-foreground">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: entry.color ?? "var(--chart-cat-1)" }}
              />
              {entry.name ?? "Series"}
            </span>
            <span className="font-medium text-foreground">
              {typeof entry.value === "number"
                ? `${formatNumber(entry.value, 1)}${valueSuffix}`
                : "--"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
