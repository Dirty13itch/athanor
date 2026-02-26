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
    },
    actions: (data.actions ?? []).map((a) => ({
      action: a.action,
      title: a.title,
    })),
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

// Notification click: open the relevant page
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url ?? "/";

  if (event.action === "approve" || event.action === "reject") {
    // Handle approval/rejection inline via API
    const taskId = event.notification.data?.taskId;
    if (taskId) {
      event.waitUntil(
        fetch(`/api/tasks/${taskId}/${event.action}`, { method: "POST" })
      );
    }
    return;
  }

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clients) => {
        const client = clients.find((c) => c.url.includes(url));
        if (client) return client.focus();
        return self.clients.openWindow(url);
      })
  );
});
