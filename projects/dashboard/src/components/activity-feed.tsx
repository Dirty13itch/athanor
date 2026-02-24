interface ActivityItem {
  type: "generation" | "download" | "stream" | "agent" | "system";
  source: string;
  title: string;
  detail: string;
  timestamp: string;
  thumbnail?: string;
  link?: string;
}

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function typeIcon(type: ActivityItem["type"]): string {
  switch (type) {
    case "generation": return "🖼";
    case "download": return "↓";
    case "stream": return "▶";
    case "agent": return "⚡";
    case "system": return "⚙";
  }
}

export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  if (items.length === 0) {
    return (
      <p className="text-xs text-muted-foreground py-2">No recent activity.</p>
    );
  }

  return (
    <div className="space-y-1.5">
      {items.map((item, i) => (
        <div key={i} className="flex items-start gap-2 text-xs">
          <span className="shrink-0 w-4 text-center" aria-hidden>{typeIcon(item.type)}</span>
          <span className="text-muted-foreground shrink-0 w-14 font-mono">{timeAgo(item.timestamp)}</span>
          <div className="min-w-0 flex-1">
            <span className="font-medium">{item.source}:</span>{" "}
            {item.link ? (
              <a href={item.link} className="text-primary hover:underline underline-offset-2">
                {item.title}
              </a>
            ) : (
              <span>{item.title}</span>
            )}
            {item.detail && (
              <span className="text-muted-foreground"> — {item.detail}</span>
            )}
          </div>
          {item.thumbnail && (
            <img
              src={item.thumbnail}
              alt=""
              className="h-6 w-6 rounded object-cover shrink-0"
            />
          )}
        </div>
      ))}
    </div>
  );
}

export type { ActivityItem };
