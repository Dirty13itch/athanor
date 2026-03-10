import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { config } from "@/lib/config";

const COLLECTION = "personal_data";

interface QdrantPoint {
  id: string | number;
  payload: {
    title?: string;
    name?: string;
    url?: string;
    source?: string;
    category?: string;
    subcategory?: string;
    indexed_at?: string;
    description?: string;
    type?: string;
  };
}

interface ScrollResponse {
  result: {
    points: QdrantPoint[];
    next_page_offset: string | number | null;
  };
}

async function getRecentItems(limit: number = 10): Promise<QdrantPoint[]> {
  try {
    // Qdrant scroll with ordering by payload field requires a specific approach.
    // We'll scroll a batch and sort client-side since personal_data is <1000 points.
    const res = await fetch(`${config.qdrant.url}/collections/${COLLECTION}/points/scroll`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        limit: 200,
        with_payload: true,
        with_vector: false,
      }),
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 60 },
    });

    if (!res.ok) return [];
    const data: ScrollResponse = await res.json();
    const points = data.result?.points ?? [];

    // Sort by indexed_at descending
    return points
      .filter((p) => p.payload?.indexed_at)
      .sort((a, b) => {
        const aTime = new Date(a.payload.indexed_at!).getTime();
        const bTime = new Date(b.payload.indexed_at!).getTime();
        return bTime - aTime;
      })
      .slice(0, limit);
  } catch {
    return [];
  }
}

export async function RecentItems() {
  const items = await getRecentItems(10);

  if (items.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Recently Indexed</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">No items found</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Recently Indexed</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {items.map((item) => {
            const p = item.payload;
            const title = p.title || p.name || "Untitled";
            const time = p.indexed_at ? formatRelativeTime(p.indexed_at) : "";

            return (
              <div
                key={item.id}
                className="flex items-start justify-between gap-3 py-1.5 border-b border-border last:border-0"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    {p.url ? (
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-medium truncate hover:underline text-primary"
                      >
                        {title}
                      </a>
                    ) : (
                      <span className="text-xs font-medium truncate">{title}</span>
                    )}
                    {p.subcategory && (
                      <Badge variant="outline" className="text-[10px] shrink-0">
                        {p.subcategory}
                      </Badge>
                    )}
                  </div>
                  {p.description && (
                    <p className="text-[10px] text-muted-foreground line-clamp-1 mt-0.5">
                      {p.description}
                    </p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                    {time}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
