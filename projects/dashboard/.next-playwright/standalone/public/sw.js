// Athanor Command Center — Service Worker
// Handles push notifications and offline fallback

const CACHE_NAME = "athanor-v1";

// Install: cache the offline fallback
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(["/offline"]))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch: network-first, fall back to offline page for navigation
self.addEventListener("fetch", (event) => {
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() => caches.match("/offline"))
    );
  }
});

// Push notification handler
self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {};
  const title = data.title ?? "Athanor";
  const options = {
    body: data.body ?? "",
    icon: "/icons/icon-192.png",
    badge: "/icons/icon-192.png",
    tag: data.tag ?? "default",
    data: {
      url: data.url ?? "/",
      actions: data.actions ?? [],
      ...(data.data ?? {}),
    },
    actions: (data.actions ?? []).map((a) => ({
      action: a.action,
      title: a.title,
    })),
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

function focusOrOpen(url) {
  return self.clients
    .matchAll({ type: "window", includeUncontrolled: true })
    .then((clients) => {
      const client = clients.find((c) => c.url.includes(url));
      if (client) return client.focus();
      return self.clients.openWindow(url);
    });
}

// Notification click: open the relevant page
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url ?? "/";

  if (event.action === "approve" || event.action === "reject") {
    const notificationId = event.notification.data?.notificationId;
    if (notificationId) {
      event.waitUntil(
        Promise.all([
          fetch(`/api/workforce/notifications/${notificationId}/resolve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ approved: event.action === "approve" }),
          }),
          focusOrOpen(url),
        ])
      );
      return;
    }
  }

  if (event.action === "feedback_up" || event.action === "feedback_down") {
    const agent = event.notification.data?.agent ?? "unknown";
    const content = event.notification.data?.content ?? event.notification.body ?? "";
    event.waitUntil(
      Promise.all([
        fetch("/api/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            feedback_type: event.action === "feedback_up" ? "thumbs_up" : "thumbs_down",
            message_content: content.substring(0, 500),
            agent: agent,
          }),
        }),
        focusOrOpen(url),
      ])
    );
    return;
  }

  event.waitUntil(focusOrOpen(url));
});
