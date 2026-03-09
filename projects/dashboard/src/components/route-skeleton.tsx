export function RouteSkeleton({
  blocks = 4,
  tall = false,
}: {
  blocks?: number;
  tall?: boolean;
}) {
  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <div className="h-3 w-28 animate-pulse rounded-full bg-muted/70" />
        <div className="h-10 w-80 animate-pulse rounded-full bg-muted/70" />
        <div className="h-5 w-[32rem] max-w-full animate-pulse rounded-full bg-muted/60" />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: blocks }).map((_, index) => (
          <div
            key={index}
            className={`animate-pulse rounded-2xl border border-border/60 bg-card/60 ${
              tall ? "h-40" : "h-28"
            }`}
          />
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <div className="h-[24rem] animate-pulse rounded-2xl border border-border/60 bg-card/60" />
        <div className="h-[24rem] animate-pulse rounded-2xl border border-border/60 bg-card/60" />
      </div>
    </div>
  );
}
