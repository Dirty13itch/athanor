import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { config } from "@/lib/config";

const COLLECTION = "personal_data";

interface ScrollResponse {
  result: {
    points: { payload: Record<string, unknown> }[];
    next_page_offset: string | number | null;
  };
}

async function countByField(field: string): Promise<Record<string, number>> {
  const counts: Record<string, number> = {};
  let offset: string | number | null = null;
  let pages = 0;

  // Scroll through all points (paginated) to count by field
  // This is more reliable than Qdrant's group API for small collections
  do {
    const body: Record<string, unknown> = {
      limit: 100,
      with_payload: { include: [field, "source"] },
      with_vector: false,
    };
    if (offset !== null) body.offset = offset;

    try {
      const res = await fetch(`${config.qdrant.url}/collections/${COLLECTION}/points/scroll`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(5000),
        next: { revalidate: 120 },
      });

      if (!res.ok) break;
      const data: ScrollResponse = await res.json();
      const points = data.result?.points ?? [];

      for (const point of points) {
        const value = (point.payload?.[field] as string) ?? "uncategorized";
        counts[value] = (counts[value] ?? 0) + 1;
      }

      offset = data.result?.next_page_offset ?? null;
      pages++;
    } catch {
      break;
    }
  } while (offset !== null && pages < 20);

  return counts;
}

export async function CategoryOverview() {
  const subcategories = await countByField("subcategory");

  // Sort by count descending
  const sorted = Object.entries(subcategories)
    .sort(([, a], [, b]) => b - a);

  const total = sorted.reduce((sum, [, count]) => sum + count, 0);

  if (sorted.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Categories</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">No data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Categories</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
          {sorted.map(([name, count]) => {
            const pct = total > 0 ? ((count / total) * 100).toFixed(0) : "0";
            return (
              <div
                key={name}
                className="rounded-lg border border-border p-3 space-y-1"
              >
                <p className="text-xs font-medium truncate" title={name}>
                  {formatCategoryName(name)}
                </p>
                <div className="flex items-baseline justify-between">
                  <span className="text-lg font-semibold">{count}</span>
                  <span className="text-[10px] text-muted-foreground">{pct}%</span>
                </div>
                <div className="h-1 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary/60"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function formatCategoryName(name: string): string {
  return name
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
