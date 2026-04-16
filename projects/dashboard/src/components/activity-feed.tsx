"use client";

import Image from "next/image";

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
    case "generation":
      return "GEN";
    case "download":
      return "DL";
    case "stream":
      return "PLAY";
    case "agent":
      return "BOT";
    case "system":
      return "SYS";
  }
}

export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  if (items.length === 0) {
    return <p className="py-2 text-xs text-muted-foreground">No recent activity.</p>;
  }

  return (
    <div className="space-y-1.5">
      {items.map((item, i) => (
        <div key={i} className="flex items-start gap-2 text-xs">
          <span className="w-10 shrink-0 text-center font-mono text-[10px] tracking-wide text-muted-foreground" aria-hidden>
            {typeIcon(item.type)}
          </span>
          <span className="w-14 shrink-0 font-mono text-muted-foreground">{timeAgo(item.timestamp)}</span>
          <div className="min-w-0 flex-1">
            <span className="font-medium">{item.source}:</span>{" "}
            {item.link ? (
              <a href={item.link} className="text-primary underline-offset-2 hover:underline">
                {item.title}
              </a>
            ) : (
              <span>{item.title}</span>
            )}
            {item.detail ? <span className="text-muted-foreground">: {item.detail}</span> : null}
          </div>
          {item.thumbnail ? (
            <Image
              src={item.thumbnail}
              alt=""
              width={24}
              height={24}
              className="h-6 w-6 shrink-0 rounded object-cover"
              unoptimized
            />
          ) : null}
        </div>
      ))}
    </div>
  );
}

export type { ActivityItem };
