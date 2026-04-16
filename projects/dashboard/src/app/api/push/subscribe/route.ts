import { NextRequest, NextResponse } from "next/server";
import {
  removePushSubscription,
  type PushSubscriptionRecord,
  upsertPushSubscription,
} from "../store";

// In-memory store for push subscriptions (in production, use Redis/DB)
// For a single-user homelab, this is fine — subscriptions survive until container restart

export async function POST(request: NextRequest) {
  try {
    const sub: PushSubscriptionRecord = await request.json();
    if (!sub.endpoint || !sub.keys?.p256dh || !sub.keys?.auth) {
      return NextResponse.json({ error: "Invalid subscription" }, { status: 400 });
    }
    return NextResponse.json({ ok: true, count: upsertPushSubscription(sub) });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { endpoint } = await request.json();
    removePushSubscription(endpoint);
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}
