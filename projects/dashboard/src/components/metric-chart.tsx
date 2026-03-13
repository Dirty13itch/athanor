import dynamic from "next/dynamic";

interface SeriesDefinition {
  dataKey: string;
  label: string;
  color: string;
}

const MetricChartClient = dynamic(
  () => import("@/components/metric-chart-client").then((module) => module.MetricChartClient),
  {
    ssr: false,
    loading: () => <div className="surface-instrument h-64 min-h-64 w-full rounded-2xl border" />,
  }
);

export function MetricChart({
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
  return (
    <MetricChartClient
      data={data}
      series={series}
      mode={mode}
      valueSuffix={valueSuffix}
    />
  );
}
