import { Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SearchBar } from "@/components/personal-data/search-bar";
import { CategoryOverview } from "@/components/personal-data/category-overview";
import { GraphSummary } from "@/components/personal-data/graph-summary";
import { RecentItems } from "@/components/personal-data/recent-items";

export const revalidate = 60;

const QDRANT_URL = "http://192.168.1.244:6333";
const COLLECTION = "personal_data";

interface QdrantCollectionInfo {
  result: {
    points_count: number;
    vectors_count: number;
    segments_count: number;
    status: string;
  };
}

async function getCollectionStats() {
  try {
    const res = await fetch(`${QDRANT_URL}/collections/${COLLECTION}`, {
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    const data: QdrantCollectionInfo = await res.json();
    return data.result;
  } catch {
    return null;
  }
}

function SectionSkeleton({ height = "h-32" }: { height?: string }) {
  return <div className={`${height} rounded-xl bg-muted/30 animate-pulse`} />;
}

export default async function PersonalDataPage() {
  const stats = await getCollectionStats();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Personal Data</h1>
          <p className="text-muted-foreground">
            Bookmarks, repos, and knowledge graph
          </p>
        </div>
        <div className="flex items-center gap-2">
          {stats ? (
            <>
              <Badge variant="outline" className="text-xs">
                {stats.points_count.toLocaleString()} items
              </Badge>
              <Badge
                variant={stats.status === "green" ? "default" : "destructive"}
                className="text-xs"
              >
                {stats.status === "green" ? "Healthy" : stats.status}
              </Badge>
            </>
          ) : (
            <Badge variant="destructive" className="text-xs">
              Qdrant Offline
            </Badge>
          )}
        </div>
      </div>

      {/* Stats overview */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Total Items" value={stats.points_count} />
          <StatCard label="Vectors" value={stats.vectors_count} />
          <StatCard label="Segments" value={stats.segments_count} />
          <StatCard label="Collection" value={COLLECTION} isText />
        </div>
      )}

      {/* Semantic search */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Semantic Search</CardTitle>
        </CardHeader>
        <CardContent>
          <SearchBar />
        </CardContent>
      </Card>

      {/* Two-column layout: graph + recent */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Suspense fallback={<SectionSkeleton height="h-48" />}>
          <GraphSummary />
        </Suspense>
        <Suspense fallback={<SectionSkeleton height="h-48" />}>
          <RecentItems />
        </Suspense>
      </div>

      {/* Category breakdown */}
      <Suspense fallback={<SectionSkeleton height="h-64" />}>
        <CategoryOverview />
      </Suspense>
    </div>
  );
}

function StatCard({
  label,
  value,
  isText = false,
}: {
  label: string;
  value: number | string;
  isText?: boolean;
}) {
  return (
    <Card className="py-3">
      <CardContent className="px-4 py-0">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">
          {label}
        </p>
        <p className={`font-semibold ${isText ? "text-sm font-mono" : "text-xl"}`}>
          {typeof value === "number" ? value.toLocaleString() : value}
        </p>
      </CardContent>
    </Card>
  );
}
