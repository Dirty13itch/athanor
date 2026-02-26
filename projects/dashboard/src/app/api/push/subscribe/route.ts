import { NextRequest, NextResponse } from "next/server";

// In-memory store for push subscriptions (in production, use Redis/DB)
// For a single-user homelab, this is fine — subscriptions survive until container restart
const subscriptions = new Map<string, PushSubscription>();

export interface PushSubscription {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
}

export async function POST(request: NextRequest) {
  try {
    const sub: PushSubscription = await request.json();
    if (!sub.endpoint || !sub.keys?.p256dh || !sub.keys?.auth) {
      return NextResponse.json({ error: "Invalid subscription" }, { status: 400 });
    }
    // Use endpoint as unique key
    subscriptions.set(sub.endpoint, sub);
    return NextResponse.json({ ok: true, count: subscriptions.size });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { endpoint } = await request.json();
    subscriptions.delete(endpoint);
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}

// Export for use by the send endpoint
export function getSubscriptions(): PushSubscription[] {
  return Array.from(subscriptions.values());
}
