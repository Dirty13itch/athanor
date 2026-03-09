"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export function PushManager() {
  const [subscribed, setSubscribed] = useState(false);
  const supported = useSyncExternalStore(
    () => () => {},
    () =>
      typeof window !== "undefined" &&
      "serviceWorker" in navigator &&
      "PushManager" in window &&
      Boolean(VAPID_PUBLIC_KEY),
    () => false
  );

  useEffect(() => {
    if (!supported) return;

    let active = true;
    navigator.serviceWorker.ready
      .then((reg) => reg.pushManager.getSubscription())
      .then((sub) => {
        if (active && sub) {
          setSubscribed(true);
        }
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, [supported]);

  async function subscribe() {
    try {
      const reg = await navigator.serviceWorker.ready;
      const keyBytes = urlBase64ToUint8Array(VAPID_PUBLIC_KEY);
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: keyBytes.buffer as ArrayBuffer,
      });

      const json = sub.toJSON();
      await fetch("/api/push/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint: json.endpoint,
          keys: json.keys,
        }),
      });

      setSubscribed(true);
    } catch (err) {
      console.error("Push subscription failed:", err);
    }
  }

  async function unsubscribe() {
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        await fetch("/api/push/subscribe", {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ endpoint: sub.endpoint }),
        });
        await sub.unsubscribe();
      }
      setSubscribed(false);
    } catch (err) {
      console.error("Push unsubscribe failed:", err);
    }
  }

  if (!supported) return null;

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-muted-foreground">Push Notifications</span>
      <button
        onClick={subscribed ? unsubscribe : subscribe}
        className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
          subscribed
            ? "bg-muted text-muted-foreground hover:bg-destructive/20 hover:text-destructive"
            : "bg-primary text-primary-foreground hover:bg-primary/90"
        }`}
      >
        {subscribed ? "Disable" : "Enable"}
      </button>
    </div>
  );
}
