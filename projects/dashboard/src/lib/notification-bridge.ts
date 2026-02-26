import webpush from "web-push";
import { getSubscriptions } from "@/app/api/push/subscribe/route";
import { config } from "./config";

const VAPID_PUBLIC = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";
const VAPID_PRIVATE = process.env.VAPID_PRIVATE_KEY ?? "";

if (VAPID_PUBLIC && VAPID_PRIVATE) {
  webpush.setVapidDetails("mailto:athanor@homelab.local", VAPID_PUBLIC, VAPID_PRIVATE);
}

interface Notification {
  id: string;
  tier: string;
  agent: string;
  category: string;
  action: string;
  details: string;
  resolved: boolean;
  created_at: string;
}

interface NotificationSummary {
  pending: number;
  total: number;
  latestAsk: Notification | null;
}

// Module-level state (persists across requests in the same Node.js process)
const pushedIds = new Set<string>();
let lastSummary: NotificationSummary = { pending: 0, total: 0, latestAsk: null };
let pollingStarted = false;

async function fetchNotifications(): Promise<Notification[]> {
  try {
    const res = await fetch(`${config.agentServer.url}/v1/notifications`, {
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.notifications ?? data ?? [];
  } catch {
    return [];
  }
}

async function sendPush(notification: Notification) {
  const subs = getSubscriptions();
  if (subs.length === 0) return;

  const tierLabel = notification.tier === "ask" ? "Needs Approval" : "Notice";
  const payload = JSON.stringify({
    title: `${tierLabel}: ${notification.agent}`,
    body: `${notification.action} — ${notification.details}`,
    tag: `escalation-${notification.id}`,
    url: "/notifications",
    actions: notification.tier === "ask"
      ? [
          { action: "approve", title: "Approve" },
          { action: "reject", title: "Reject" },
        ]
      : [],
  });

  await Promise.allSettled(
    subs.map((sub) =>
      webpush.sendNotification({ endpoint: sub.endpoint, keys: sub.keys }, payload)
    )
  );
}

async function pollNotifications() {
  const notifications = await fetchNotifications();
  const unresolved = notifications.filter((n) => !n.resolved);
  const askNotifications = unresolved.filter((n) => n.tier === "ask");

  lastSummary = {
    pending: unresolved.length,
    total: notifications.length,
    latestAsk: askNotifications[0] ?? null,
  };

  // Push new "ask" and "notify" tier notifications
  for (const n of unresolved) {
    if ((n.tier === "ask" || n.tier === "notify") && !pushedIds.has(n.id)) {
      pushedIds.add(n.id);
      await sendPush(n);
    }
  }

  // Clean up pushed IDs for resolved notifications (prevent unbounded growth)
  const activeIds = new Set(notifications.map((n) => n.id));
  for (const id of pushedIds) {
    if (!activeIds.has(id)) pushedIds.delete(id);
  }
}

export function startNotificationBridge() {
  if (pollingStarted) return;
  pollingStarted = true;
  // Poll every 30 seconds
  setInterval(pollNotifications, 30_000);
  // Initial poll after 5s (let server settle)
  setTimeout(pollNotifications, 5_000);
}

export function getNotificationSummary(): NotificationSummary {
  return lastSummary;
}
