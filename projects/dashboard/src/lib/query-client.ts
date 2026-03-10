export const queryKeys = {
  overview: ["overview"] as const,
  workforce: ["workforce"] as const,
  services: ["services"] as const,
  servicesHistory: (window: string) => ["services-history", window] as const,
  gpuSnapshot: ["gpu-snapshot"] as const,
  gpuHistory: (window: string) => ["gpu-history", window] as const,
  models: ["models"] as const,
  agents: ["agents"] as const,
};
