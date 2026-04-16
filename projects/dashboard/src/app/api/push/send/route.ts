import { NextRequest, NextResponse } from "next/server";
import webpush from "web-push";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";
import { listPushSubscriptions } from "../store";

const VAPID_PUBLIC = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";
const VAPID_PRIVATE = process.env.VAPID_PRIVATE_KEY ?? "";

if (VAPID_PUBLIC && VAPID_PRIVATE) {
  webpush.setVapidDetails("mailto:athanor@homelab.local", VAPID_PUBLIC, VAPID_PRIVATE);
}

export async function POST(request: NextRequest) {
  if (isDashboardFixtureMode()) {
    const subs = listPushSubscriptions();
    return NextResponse.json({
      sent: subs.length,
      failed: 0,
      total: subs.length,
      fixture: true,
    });
  }

  if (!VAPID_PUBLIC || !VAPID_PRIVATE) {
    return NextResponse.json({ error: "VAPID keys not configured" }, { status: 500 });
  }

  try {
    const { title, body, tag, url, actions, data } = await request.json();

    const payload = JSON.stringify({
      title: title ?? "Athanor",
      body: body ?? "",
      tag: tag ?? "default",
      url: url ?? "/",
      actions: actions ?? [],
      data: data ?? {},
    });

    const subs = listPushSubscriptions();
    if (subs.length === 0) {
      return NextResponse.json({ error: "No subscriptions", sent: 0 });
    }

    const results = await Promise.allSettled(
      subs.map((sub) =>
        webpush.sendNotification(
          { endpoint: sub.endpoint, keys: sub.keys },
          payload
        )
      )
    );

    const sent = results.filter((r) => r.status === "fulfilled").length;
    const failed = results.filter((r) => r.status === "rejected").length;

    return NextResponse.json({ sent, failed, total: subs.length });
  } catch {
    return NextResponse.json({ error: "Send failed" }, { status: 500 });
  }
}
