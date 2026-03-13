export const LIVE_REFRESH_INTERVALS = {
  overview: 15_000,
  telemetry: 10_000,
} as const;

export function liveQueryOptions(intervalMs: number) {
  return {
    refetchInterval: intervalMs,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    staleTime: Math.max(1_000, Math.floor(intervalMs / 2)),
  } as const;
}

export function formatRefreshCadence(intervalMs: number) {
  if (intervalMs % 60_000 === 0) {
    const minutes = intervalMs / 60_000;
    return `${minutes}m`;
  }

  return `${Math.round(intervalMs / 1_000)}s`;
}
