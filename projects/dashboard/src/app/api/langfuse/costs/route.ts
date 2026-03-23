import { config } from "@/lib/config";

interface LangfuseGeneration {
  id: string;
  model: string | null;
  calculatedTotalCost: number | null;
  totalTokens: number;
  promptTokens: number;
  completionTokens: number;
  startTime: string;
  level: string;
}

interface ModelCosts {
  model: string;
  totalCost: number;
  requestCount: number;
  totalTokens: number;
  promptTokens: number;
  completionTokens: number;
  errorCount: number;
}

interface TimeBucket {
  label: string;
  since: string;
  totalCost: number;
  requestCount: number;
  totalTokens: number;
}

async function fetchGenerations(since: string): Promise<LangfuseGeneration[]> {
  const { url, publicKey, secretKey } = config.langfuse;
  const creds = Buffer.from(`${publicKey}:${secretKey}`).toString("base64");

  const all: LangfuseGeneration[] = [];
  let page = 1;
  const limit = 100;

  // Paginate through all generations since the given timestamp
  while (page <= 20) {
    const params = new URLSearchParams({
      limit: String(limit),
      page: String(page),
      type: "GENERATION",
      fromStartTime: since,
    });

    const res = await fetch(`${url}/api/public/observations?${params}`, {
      headers: { Authorization: `Basic ${creds}` },
      signal: AbortSignal.timeout(15000),
    });

    if (!res.ok) {
      break;
    }

    const body = await res.json();
    const data = body.data as LangfuseGeneration[] | undefined;
    if (!data || data.length === 0) {
      break;
    }
    all.push(...data);

    if (data.length < limit) {
      break;
    }
    page += 1;
  }

  return all;
}

function aggregate(generations: LangfuseGeneration[]): {
  byModel: ModelCosts[];
  totalCost: number;
  requestCount: number;
  totalTokens: number;
} {
  const map = new Map<string, Omit<ModelCosts, "model">>();

  let totalCost = 0;
  let requestCount = 0;
  let totalTokens = 0;

  for (const g of generations) {
    const model = g.model || "unknown";
    const cost = g.calculatedTotalCost ?? 0;

    totalCost += cost;
    requestCount += 1;
    totalTokens += g.totalTokens ?? 0;

    const existing = map.get(model) ?? {
      totalCost: 0,
      requestCount: 0,
      totalTokens: 0,
      promptTokens: 0,
      completionTokens: 0,
      errorCount: 0,
    };

    existing.totalCost += cost;
    existing.requestCount += 1;
    existing.totalTokens += g.totalTokens ?? 0;
    existing.promptTokens += g.promptTokens ?? 0;
    existing.completionTokens += g.completionTokens ?? 0;
    if (g.level === "ERROR") {
      existing.errorCount += 1;
    }

    map.set(model, existing);
  }

  const byModel: ModelCosts[] = Array.from(map.entries())
    .map(([model, stats]) => ({ model, ...stats }))
    .sort((a, b) => b.requestCount - a.requestCount);

  return { byModel, totalCost, requestCount, totalTokens };
}

export async function GET() {
  try {
    const now = new Date();
    const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString();
    const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();

    // Fetch all generations from the last 30 days
    const allGenerations = await fetchGenerations(monthAgo);

    // Split into time buckets
    const gens24h = allGenerations.filter((g) => g.startTime >= dayAgo);
    const gens7d = allGenerations.filter((g) => g.startTime >= weekAgo);

    const agg24h = aggregate(gens24h);
    const agg7d = aggregate(gens7d);
    const agg30d = aggregate(allGenerations);

    const buckets: TimeBucket[] = [
      { label: "24h", since: dayAgo, ...agg24h },
      { label: "7d", since: weekAgo, ...agg7d },
      { label: "30d", since: monthAgo, ...agg30d },
    ];

    return Response.json({
      generatedAt: now.toISOString(),
      buckets,
      byModel: agg30d.byModel,
      totalGenerations: allGenerations.length,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to fetch Langfuse costs";
    return Response.json({ error: message }, { status: 502 });
  }
}
