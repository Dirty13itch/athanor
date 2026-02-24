import { queryPrometheusRange } from "@/lib/api";

export async function GET() {
  const now = Math.floor(Date.now() / 1000);
  const oneHourAgo = now - 3600;
  const step = 60; // 1-minute resolution

  try {
    const [utilization, temperature, power] = await Promise.all([
      queryPrometheusRange("DCGM_FI_DEV_GPU_UTIL", oneHourAgo, now, step).catch(() => []),
      queryPrometheusRange("DCGM_FI_DEV_GPU_TEMP", oneHourAgo, now, step).catch(() => []),
      queryPrometheusRange("DCGM_FI_DEV_POWER_USAGE", oneHourAgo, now, step).catch(() => []),
    ]);

    // Transform into a map: instance::gpu_index -> { utilization: number[], temperature: number[], power: number[] }
    const gpuHistory: Record<
      string,
      {
        instance: string;
        gpu: string;
        gpuName: string;
        utilization: number[];
        temperature: number[];
        power: number[];
      }
    > = {};

    function processMetric(
      results: { metric: Record<string, string>; values: [number, string][] }[],
      field: "utilization" | "temperature" | "power"
    ) {
      for (const r of results) {
        const instance = r.metric.instance ?? "";
        const gpu = r.metric.gpu ?? r.metric.gpu_bus_id ?? "";
        const key = `${instance}::${gpu}`;
        if (!gpuHistory[key]) {
          gpuHistory[key] = {
            instance,
            gpu,
            gpuName: r.metric.modelName ?? r.metric.gpu_name ?? "GPU",
            utilization: [],
            temperature: [],
            power: [],
          };
        }
        gpuHistory[key][field] = r.values.map(([, v]) => parseFloat(v));
      }
    }

    processMetric(utilization, "utilization");
    processMetric(temperature, "temperature");
    processMetric(power, "power");

    return Response.json({ gpus: gpuHistory });
  } catch {
    return Response.json({ gpus: {} });
  }
}
