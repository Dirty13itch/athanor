# Mobile-First PWA Architecture for Real-Time Dashboards

**Date:** 2026-02-25
**Status:** Complete -- recommendation ready
**Supports:** Future ADR (Mobile PWA Dashboard)
**Depends on:** ADR-007 (Dashboard), ADR-016 (Remote Access)

---

## Context

The Athanor dashboard (Next.js 16, React 19, Tailwind CSS v4, shadcn/ui) runs at Node 2:3001 with 16 pages, 26+ service health checks, and real-time monitoring of 8 AI agents, 7 GPUs, and the full homelab infrastructure. Currently desktop-only with a fixed 224px sidebar and no mobile handling. The goal is to make it genuinely useful on a phone -- not just responsive, but designed for mobile interaction including push notifications, offline awareness, and touch-optimized controls.

---

## 1. PWA Capabilities in 2026

### What PWAs Can Do Now

Progressive Web Apps in 2026 cover the vast majority of what a dashboard needs:

| Capability | Android | iOS (16.4+) | Desktop |
|---|---|---|---|
| Install to home screen | Full | Full | Full (macOS, Windows, Chrome OS) |
| Push notifications | Full | Partial (home screen only) | Full |
| Offline caching | Full | Full | Full |
| Background sync | Full | Limited | Full |
| Standalone display (no browser chrome) | Full | Full | Full |
| App badges | Full | Full | Full |
| Geolocation | Full | Full | Full |
| Biometric auth (WebAuthn) | Full | Full | Full |
| Vibration/haptic | Full | Not supported | N/A |
| Camera/microphone | Full | Full | Full |
| File system access | Full | Full | Full |
| Share to/from other apps | Full | Partial | Full |

### iOS-Specific Limitations (Still Present)

iOS remains the weaker PWA platform, but for a dashboard use case the gaps are manageable:

1. **Push notifications require home screen install.** The user must add the PWA to their home screen before push works. Not a problem for a personal dashboard -- Shaun will install it once.
2. **No silent/background push.** Safari requires immediately showing a notification to the user. If you receive a push event and don't display a notification, Safari revokes permission. This means no background data sync via push.
3. **No Vibration API.** The Web Vibration API is not available on iOS at all. Haptic feedback only works on Android.
4. **Limited background execution.** When the PWA is not in the foreground, iOS aggressively suspends it. No background location, no background audio recording, no long-running tasks.
5. **Storage eviction.** iOS can evict cached data from PWAs if the device is under storage pressure, though this is rare for actively-used apps.
6. **No Periodic Background Sync on iOS.** Chrome on Android supports `periodicSync`, iOS does not.

### Assessment for Athanor

A PWA is the right choice. The dashboard is a read-heavy monitoring app with occasional control actions (trigger agent, approve notification). It does not need Bluetooth, NFC, ARKit, or in-app purchases. The iOS push notification limitation (home screen install required) is a non-issue for a single-user homelab.

**Sources:**
- [Brainhub: PWA on iOS -- Current Status & Limitations (2025)](https://brainhub.eu/library/pwa-on-ios)
- [Mobiloud: Progressive Web Apps on iOS (2026)](https://www.mobiloud.com/blog/progressive-web-apps-ios)
- [Progressier: PWA vs Native App Comparison Table (2026)](https://progressier.com/pwa-vs-native-app-comparison-table)
- [10 Grounds: Pros and Cons of PWAs (2025)](https://www.10grounds.com/blog/the-pros-and-cons-of-progressive-web-apps-pwas-in-2025)

---

## 2. Next.js 16 PWA Implementation

### Library Landscape

| Library | Status | Next.js 16 | Bundler | Notes |
|---|---|---|---|---|
| `next-pwa` (shadowwalker) | Abandoned | No | Webpack only | Last commit 2023. Do not use. |
| `@ducanh2912/next-pwa` | Maintenance | Partial | Webpack only | Fork of next-pwa with bug fixes. Being superseded by Serwist. |
| **Serwist** (`@serwist/next`) | Active | Yes | Webpack only | Modern rewrite built on Workbox. Official Next.js docs reference it. Recommended. |
| Manual service worker | Always works | Yes | Any | Next.js official PWA guide uses manual `public/sw.js`. No build integration needed. |

### Critical Constraint: Turbopack vs Webpack

Next.js 16 defaults to Turbopack for development. Serwist requires Webpack for the build step. This is a real friction point:

- **Development:** Serwist does not work with Turbopack. Dev must use `next dev --webpack` to test service worker behavior.
- **Production build:** `next build` uses webpack by default (Turbopack is dev-only default), so production builds work fine with Serwist.
- **Workaround:** Use Turbopack for regular development (fast HMR), switch to `--webpack` only when testing PWA/offline features. Add both scripts to package.json.

### Recommended Approach: Hybrid (Manual SW + Serwist for Precaching)

Given Athanor's needs (real-time dashboard, push notifications, basic offline), the recommended approach is:

**Option A -- Manual Service Worker (Simpler, Recommended)**

Use Next.js's built-in PWA guide. Create `public/sw.js` manually. Handle push events, basic caching, and offline fallback directly. No build plugin needed. Works with both Turbopack and Webpack.

Pros: No build tool dependency. Full control. Official Next.js pattern.
Cons: No automatic precaching of build assets. Must manually define cache strategies.

**Option B -- Serwist (More Automated)**

Use `@serwist/next` to wrap the Next.js config. Gets automatic precaching of all build output, configurable runtime caching strategies, and offline fallback pages.

Pros: Automatic precaching. Rich caching strategy primitives. Well-maintained.
Cons: Requires webpack for builds. Adds build complexity. One more dependency.

**Recommendation:** Start with Option A (manual service worker) for push notifications and basic caching. Upgrade to Serwist later if offline support becomes important. For a homelab dashboard that's always on the LAN, offline support is low priority.

### Manifest Configuration

```typescript
// app/manifest.ts
import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Athanor',
    short_name: 'Athanor',
    description: 'Homelab command center',
    start_url: '/',
    display: 'standalone',
    background_color: '#0d0d0d',  // matches --background in dark mode
    theme_color: '#0d0d0d',
    icons: [
      {
        src: '/icons/icon-192x192.png',
        sizes: '192x192',
        type: 'image/png',
      },
      {
        src: '/icons/icon-512x512.png',
        sizes: '512x512',
        type: 'image/png',
      },
      {
        src: '/icons/icon-512x512-maskable.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'maskable',
      },
    ],
  }
}
```

### Icon Requirements

| Size | Purpose | Notes |
|---|---|---|
| 192x192 PNG | Android install, splash | Required |
| 512x512 PNG | Android install, splash | Required |
| 512x512 PNG maskable | Android adaptive icon | Centered design with safe zone |
| 180x180 PNG | iOS apple-touch-icon | Set via `metadata.icons.apple` in layout.tsx |
| favicon.ico | Browser tab | Already exists |

### Layout Metadata Update

```typescript
// app/layout.tsx metadata addition
export const metadata: Metadata = {
  title: 'Athanor',
  description: 'Homelab command center',
  applicationName: 'Athanor',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Athanor',
  },
  formatDetection: {
    telephone: false,
  },
};

export const viewport: Viewport = {
  themeColor: '#0d0d0d',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,  // prevents double-tap zoom on interactive elements
};
```

**Sources:**
- [Next.js Official PWA Guide](https://nextjs.org/docs/app/guides/progressive-web-apps)
- [Serwist Getting Started with Next.js](https://serwist.pages.dev/docs/next/getting-started)
- [LogRocket: Build a Next.js 16 PWA with Offline Support](https://blog.logrocket.com/nextjs-16-pwa-offline-support/)
- [Aurora Scharff: PWA Icons in Next.js 16 with Serwist](https://aurorascharff.no/posts/dynamically-generating-pwa-app-icons-nextjs-16-serwist/)

---

## 3. Responsive vs Adaptive Design

### The Question

Should the dashboard be one responsive app with breakpoints, or should it serve different layouts to different devices?

### Analysis

| Approach | Pros | Cons |
|---|---|---|
| **Responsive (same app, breakpoints)** | Single codebase. One URL. Shared state/routing. Simpler deployment. | Complex components must handle all sizes. Can lead to "desktop crammed into mobile." |
| **Adaptive (different layouts per device)** | Each layout optimized for its context. Mobile can show completely different views. | More code to maintain. Risk of feature drift between layouts. |
| **Separate mobile app** | Full native experience. | Two codebases. Insane overhead for one person. |

### Recommendation: Responsive with Mobile-Specific View Modes

Use a single responsive codebase with three tiers:

1. **Desktop (>= 1024px):** Full sidebar + multi-column grid. Current design, unchanged.
2. **Tablet (768px - 1023px):** Collapsed sidebar (icon-only) + 2-column grid.
3. **Mobile (< 768px):** No sidebar. Bottom tab bar. Single-column stack. Card-based layout.

The key insight is that mobile should not just be "desktop shrunk down." The mobile experience should:
- Show a curated overview on the home screen (health summary, alert count, active agents)
- Use bottom navigation for the 5 most important sections
- Put secondary pages behind a "More" menu
- Prioritize glanceable data over detailed tables
- Use cards that can be tapped to expand, not tables that scroll horizontally

### Mobile Navigation Pattern

Replace the desktop sidebar with a bottom tab bar on mobile:

```
+-------------------------------------------+
|  Athanor           [bell] [refresh]       |  <- Top bar (minimal)
+-------------------------------------------+
|                                           |
|  [Status cards - stacked vertically]      |
|  [GPU summary - compact cards]            |
|  [Recent alerts - list]                   |
|  [Agent status - list]                    |
|                                           |
+-------------------------------------------+
|  [Home] [GPUs] [Agents] [Chat] [More]    |  <- Bottom tab bar
+-------------------------------------------+
```

The bottom tab bar should:
- Be fixed at viewport bottom (position: fixed)
- Have 5 items maximum (Apple HIG, Material Design both recommend this)
- Use 48px minimum touch targets
- Show active state with amber accent color
- Include the top 5 most-used sections (configurable)

### Implementation

The layout.tsx needs conditional rendering:

```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        {/* Desktop sidebar - hidden on mobile */}
        <div className="hidden lg:block">
          <SidebarNav />
        </div>
        {/* Main content - full width on mobile, offset on desktop */}
        <main className="min-h-screen p-4 pb-20 lg:ml-56 lg:p-6 lg:pb-6">
          {children}
        </main>
        {/* Mobile bottom nav - hidden on desktop */}
        <div className="fixed bottom-0 left-0 right-0 lg:hidden">
          <BottomNav />
        </div>
      </body>
    </html>
  );
}
```

**Sources:**
- [Toptal: Mobile Dashboard UI Best Practices](https://www.toptal.com/designers/dashboard-design/mobile-dashboard-ui)
- [Medium: 20 Dashboard UI/UX Design Principles for 2025](https://medium.com/@allclonescript/20-best-dashboard-ui-ux-design-principles-you-need-in-2025-30b661f2f795)
- [brand.dev: Dashboard Design Best Practices for SaaS (2025)](https://www.brand.dev/blog/dashboard-design-best-practices)

---

## 4. Touch-Optimized Interactions

### Touch Target Sizes

The single most important mobile UX rule: make things big enough to tap.

| Standard | Minimum Touch Target | Recommended |
|---|---|---|
| Apple HIG | 44x44 pt | 44x44 pt |
| Material Design 3 | 48x48 dp | 48x48 dp |
| WCAG 2.5.5 (AAA) | 44x44 CSS px | 44x44 CSS px |
| Current Athanor sidebar links | ~36px height | Too small for mobile |

**Action:** All interactive elements on mobile must be at minimum 44x44px. This affects buttons, nav items, list rows, card actions, and form inputs.

### Gestures

| Gesture | Use Case | Implementation |
|---|---|---|
| **Tap** | Primary action | Standard onClick. No delay needed (modern browsers removed 300ms tap delay). |
| **Pull-to-refresh** | Refresh dashboard data | CSS `overscroll-behavior` + custom handler, or native PWA behavior. |
| **Swipe left/right** | Navigate between tabs, dismiss items | `onTouchStart`/`onTouchMove`/`onTouchEnd` or a library like `react-swipeable`. |
| **Long press** | Secondary actions, context menu | `onContextMenu` or timer-based with `onTouchStart`/`onTouchEnd`. |
| **Pinch-to-zoom** | Chart zoom | Disabled globally via viewport meta, enabled per-chart with gesture handler. |

### Haptic Feedback (Vibration API)

The Web Vibration API (`navigator.vibrate()`) provides tactile feedback on supported devices:

```typescript
function haptic(pattern: 'light' | 'medium' | 'heavy' = 'light') {
  if (!('vibrate' in navigator)) return;
  const patterns = {
    light: [10],
    medium: [20],
    heavy: [30, 10, 30],
  };
  navigator.vibrate(patterns[pattern]);
}
```

**Limitation:** Works on Android (Chrome, Firefox). Does NOT work on iOS at all. For iOS, the `react-haptic` library uses a hidden `<input type="checkbox">` switch trick to trigger iOS's built-in haptic, but this is a hack with limited reliability.

**Recommendation:** Use vibration as progressive enhancement on Android. Don't design interactions that depend on it.

### Complex Interactions on Touch

| Desktop Pattern | Mobile Equivalent |
|---|---|
| Hover tooltip | Tap to reveal inline, or info icon |
| Right-click context menu | Long press, or swipe-to-reveal actions |
| Drag to reorder | Long press to activate drag mode, then drag |
| Multi-select with checkboxes | Tap to select (toggle mode), bulk actions bar appears |
| Data table with many columns | Card list with expandable details, or horizontal scroll with frozen first column |
| Sidebar navigation | Bottom tab bar + "More" sheet |

### Pull-to-Refresh Implementation

```tsx
// Simple pull-to-refresh using overscroll-behavior
// CSS: html { overscroll-behavior-y: contain; }
// This prevents the browser's native pull-to-refresh, letting us implement our own.

function usePullToRefresh(onRefresh: () => Promise<void>) {
  const [refreshing, setRefreshing] = useState(false);
  const startY = useRef(0);

  const handleTouchStart = (e: TouchEvent) => {
    if (window.scrollY === 0) {
      startY.current = e.touches[0].clientY;
    }
  };

  const handleTouchEnd = async (e: TouchEvent) => {
    const pullDistance = e.changedTouches[0].clientY - startY.current;
    if (pullDistance > 80 && window.scrollY === 0 && !refreshing) {
      setRefreshing(true);
      await onRefresh();
      setRefreshing(false);
    }
  };

  // Attach to window in useEffect...
  return { refreshing };
}
```

**Sources:**
- [CodeByUmar: Vibration API for Haptic Feedback (2025)](https://codebyumar.medium.com/how-to-use-the-vibration-api-to-add-haptic-feedback-to-mobile-web-apps-734dea37dc8f)
- [react-haptic: React hooks for haptic feedback](https://github.com/ryotanakata/react-haptic)
- [OpenReplay: Haptic Feedback for Web Apps](https://blog.openreplay.com/haptic-feedback-for-web-apps-with-the-vibration-api/)

---

## 5. Mobile Push Notification Architecture

### How Web Push Works (Without FCM)

A common misconception is that web push requires Firebase Cloud Messaging (FCM) or Apple Push Notification Service (APNs). It does not. The Web Push Protocol (RFC 8030) with VAPID authentication (RFC 8292) works directly:

```
Your Server (Next.js) --VAPID signed--> Browser Push Service ---> Client SW
```

Each browser uses its own push service internally (Chrome uses FCM, Firefox uses Mozilla Push, Safari uses APNs), but you never interact with these directly. You only need:

1. A VAPID key pair (generated once with `web-push generate-vapid-keys`)
2. The `web-push` npm package on your server
3. A service worker on the client to receive push events

### Implementation Architecture for Athanor

```
Agent API (Node 1:9000)
  |
  |-- Event occurs (agent failure, task complete, GPU alert)
  |
  v
Dashboard API Route (Node 2:3001/api/push)
  |
  |-- Looks up push subscriptions in storage
  |-- Signs payload with VAPID private key
  |-- Sends to browser push endpoint
  |
  v
Browser Push Service (automatic, transparent)
  |
  v
Service Worker (sw.js on client)
  |
  |-- self.addEventListener('push', ...)
  |-- self.registration.showNotification(...)
  |
  v
User sees notification
```

### Notification Types for Athanor

| Category | Priority | Example | Action Buttons |
|---|---|---|---|
| **Critical** | High | GPU overtemp, service down, disk full | "View Details" |
| **Agent** | Medium | Task completed, task failed, escalation | "View", "Approve/Reject" |
| **Media** | Low | New content added, transcode complete | "View in Plex" |
| **System** | Low | Backup complete, model loaded | None (informational) |

### Notification Actions (Interactive)

Service workers support action buttons directly in notifications:

```javascript
// sw.js
self.addEventListener('push', (event) => {
  const data = event.data.json();
  const options = {
    body: data.body,
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    tag: data.tag,  // groups notifications with same tag
    renotify: true,
    vibrate: [100, 50, 100],
    actions: data.actions || [],
    data: { url: data.url },
  };
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const action = event.action;
  const url = event.notification.data.url;

  if (action === 'approve') {
    // Call API to approve the task
    event.waitUntil(
      fetch('/api/tasks/approve', { method: 'POST', body: JSON.stringify({ id: event.notification.tag }) })
    );
  } else {
    // Open the dashboard to the relevant page
    event.waitUntil(clients.openWindow(url || '/'));
  }
});
```

### Subscription Storage

Store push subscriptions in Qdrant (or Redis). Schema:

```typescript
interface PushSubscription {
  endpoint: string;       // Browser push service URL
  keys: {
    p256dh: string;       // Public key for encryption
    auth: string;         // Auth secret
  };
  device: string;         // User-agent derived device name
  createdAt: string;
  lastUsed: string;
}
```

### iOS Gotchas

1. **Must install to home screen first.** Push subscription will fail if the app is accessed through Safari directly.
2. **Must show notification immediately.** If the push handler doesn't call `showNotification()`, iOS revokes push permission. No silent pushes.
3. **No notification grouping.** iOS does not support the `tag` property for grouping web push notifications the way Android does.
4. **No action buttons on iOS.** Notification `actions` are ignored on iOS Safari.

### Alternative: ntfy

ntfy.sh is a self-hosted pub-sub notification server that can also deliver push notifications. It could complement the direct Web Push approach:

- **Pros:** Has its own mobile app (reliable delivery). Simple HTTP pub-sub API (`curl -d "message" ntfy.sh/topic`). Can be self-hosted on VAULT.
- **Cons:** Adds another service to maintain. Separate notification flow from the dashboard. Not integrated with the service worker.
- **Verdict:** Consider ntfy as a fallback for critical alerts (service down, disk full) where delivery reliability matters more than integration elegance. Use Web Push for everything else.

**Sources:**
- [Next.js Official: PWA Push Notifications Guide](https://nextjs.org/docs/app/guides/progressive-web-apps)
- [Isala Piyarisi: Web Push Without Firebase](https://isala.me/blog/web-push-notifications-without-firebase/)
- [MagicBell: Complete Guide to Push Notifications in PWAs](https://www.magicbell.com/blog/using-push-notifications-in-pwas)
- [DEV.to: Self-Hosted Push Notifications](https://dev.to/bunty9/-self-hosted-push-notifications-12g5)
- [ntfy.sh](https://ntfy.sh/)

---

## 6. Real-Time Updates on Mobile

### Protocol Comparison

| Feature | WebSocket | SSE (Server-Sent Events) | Polling |
|---|---|---|---|
| Direction | Bidirectional | Server -> Client | Client -> Server |
| Connection | Persistent TCP | Persistent HTTP | New request each time |
| Auto-reconnect | Manual | Built-in | N/A (always new) |
| Binary data | Yes | No (text only, base64 for binary) | Yes |
| HTTP/2 multiplexing | No (upgrades to WS) | Yes | Yes |
| Mobile battery impact | Low (if heartbeat tuned) | Low (passive connection) | High (radio wake per request) |
| Proxy/CDN friendly | Sometimes problematic | Yes (standard HTTP) | Yes |
| Browser support | Universal | Universal | Universal |
| Current Athanor usage | Agent API WebSocket | Not used | 10s/30s intervals |

### Battery Impact Analysis

Battery drain on mobile comes from radio wake-ups. Each network request wakes the cellular/WiFi radio, which takes ~2-3 seconds to power up and ~10-15 seconds to power back down:

- **Polling every 10s:** Radio never sleeps. Constant drain. Worst option for battery.
- **WebSocket with 30s heartbeat:** Radio wakes every 30s. Moderate drain.
- **SSE with no heartbeat:** Radio stays in low-power mode between server messages. Best for battery when message frequency is low (1-2 per minute).
- **WebSocket with 60s+ heartbeat:** Comparable to SSE. Good for battery.

### Reconnection on Mobile (Sleep/Wake)

When a phone screen turns off or the app goes to background:
- iOS kills WebSocket and SSE connections after ~30 seconds in background
- Android varies by manufacturer (Doze mode, battery optimization)
- Both: the `visibilitychange` event fires when the app returns to foreground

```typescript
// Reconnection pattern for mobile
function useRealtimeConnection(url: string) {
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    const es = new EventSource(url);
    es.onmessage = (event) => { /* handle update */ };
    es.onerror = () => {
      // SSE auto-reconnects, but we can add backoff
      es.close();
      setTimeout(connect, 2000);
    };
    eventSourceRef.current = es;
  }, [url]);

  useEffect(() => {
    connect();

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        // App came back to foreground - reconnect + fetch fresh data
        eventSourceRef.current?.close();
        connect();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      eventSourceRef.current?.close();
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [connect]);
}
```

### Recommendation for Athanor

**Use SSE for dashboard real-time updates. Keep WebSocket only for bidirectional chat.**

Rationale:
1. Dashboard data is overwhelmingly server-to-client (GPU metrics, service status, agent activity).
2. SSE auto-reconnects. WebSocket requires manual reconnection logic.
3. SSE works over standard HTTP, friendlier with proxies and load balancers.
4. SSE supports HTTP/2 multiplexing -- multiple SSE streams over one connection.
5. The one bidirectional need (chat) already uses WebSocket through the chat page.

### SSE Endpoint Design

```typescript
// app/api/events/route.ts
export async function GET(request: Request) {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      // Initial state dump
      const state = await fetchDashboardState();
      controller.enqueue(encoder.encode(`data: ${JSON.stringify(state)}\n\n`));

      // Subscribe to updates (Redis pub/sub, or polling backend)
      const interval = setInterval(async () => {
        const updates = await fetchUpdates();
        if (updates) {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(updates)}\n\n`));
        }
      }, 5000);

      request.signal.addEventListener('abort', () => {
        clearInterval(interval);
        controller.close();
      });
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

**Sources:**
- [codebyte.solutions: HTTPS vs WebSockets vs SSE for Mobile Apps](https://www.codebyte.solutions/https-vs-websockets-vs-sse-a-simple-guide-for-mobile-apps/)
- [DebutInfotech: Real-Time Web Apps in 2025](https://www.debutinfotech.com/blog/real-time-web-apps)
- [portalZINE: SSE's Glorious Comeback in 2025](https://portalzine.de/sses-glorious-comeback-why-2025-is-the-year-of-server-sent-events/)
- [SoftwareMill: SSE vs WebSockets Comparison](https://softwaremill.com/sse-vs-websockets-comparing-real-time-communication-protocols/)
- [Yuri Kan: WebSocket Mobile Testing](https://yrkan.com/blog/websocket-mobile-testing/)

---

## 7. Mobile Data Visualization

### The Problem

A 6-inch phone screen is ~375x812 CSS pixels. The desktop dashboard shows 5-column grids with detailed GPU cards, sparklines, and data tables. None of this works on mobile without rethinking.

### Chart Library Comparison

| Library | Bundle Size | Responsive | Touch | Sparklines | shadcn/ui Integration | React 19 |
|---|---|---|---|---|---|---|
| **Recharts** | ~280 KB | ResponsiveContainer | Limited | Via custom | Official shadcn/ui charts use it | Yes |
| **Tremor** | ~180 KB | Built-in | Built-in | SparkChart component | Built on Tailwind + Radix | Yes |
| **Nivo** | ~350 KB+ | Built-in | Limited | Via custom | No native integration | Yes |
| **Victory** | ~200 KB | Via container | Built-in | Via VictoryLine | No native integration | Yes |
| **Custom SVG** (current) | ~1 KB | Manual | Manual | Current Sparkline component | Native | Yes |

### Recommendation: Recharts + Custom SVG

Athanor already has a custom `Sparkline` component built with inline SVG. This is the right approach for small, lightweight visualizations. For more complex charts (time-series GPU history, agent activity over time), add Recharts -- it's what shadcn/ui's chart components use internally.

Do NOT add Tremor. It's a full component library that would conflict with shadcn/ui's design system. Tremor's value proposition is "ready-made dashboard components" but Athanor already has a bespoke design system.

### Mobile Visualization Patterns

| Desktop Pattern | Mobile Equivalent |
|---|---|
| 5-column GPU grid | Horizontal scroll or 2-column compact cards |
| Detailed sparklines (120x32px) | Inline sparklines (60x20px) in list rows |
| Multi-axis time series | Single metric per chart, swipe between metrics |
| Data table with 8+ columns | Card list with key metrics, tap for detail |
| Full-width charts | Full-width charts (this actually works well on mobile) |

### Mobile GPU Card Design

Instead of the desktop GPU card with all metrics visible, the mobile card should show:

```
+-----------------------------------+
| RTX 5070 Ti #0        [87%] [==] |  <- Name, utilization, mini bar
| 12.4 / 16.3 GB  |  52C  |  185W |  <- VRAM, temp, power (one line)
+-----------------------------------+
```

Tap to expand and see: sparkline history, loaded model, process list, detailed metrics.

### Sparkline Sizing for Mobile

The existing `Sparkline` component defaults to 120x32px. For mobile list items, use 60x20px or 80x24px. The component already supports `width` and `height` props.

**Sources:**
- [LogRocket: Best React Chart Libraries (2025)](https://blog.logrocket.com/best-react-chart-libraries-2025/)
- [Tremor: SparkChart Component](https://www.tremor.so/docs/visualizations/spark-chart)
- [shadcn/ui Charts Discussion](https://github.com/shadcn-ui/ui/discussions/4133)
- [Embeddable: 8 Best React Chart Libraries (2025)](https://embeddable.com/blog/react-chart-libraries)

---

## 8. Mobile Dashboard Examples -- What Works, What Doesn't

### Home Assistant Mobile

**What it does well:**
- Card-based layout that works at any width
- "Sections" view with a Z-grid pattern (fills left-to-right, wraps)
- Tap-to-toggle for simple controls (lights, switches)
- Drag-and-drop dashboard editor
- Responsive without separate mobile/desktop layouts
- Push notifications via companion app

**What it gets wrong:**
- Dashboard editing is clunky on mobile
- Deep customization requires YAML editing
- No bottom navigation (uses sidebar/top nav)
- Charts are basic and not touch-optimized

**Relevance to Athanor:** The card-based layout with tap-to-expand is the right pattern. The Z-grid responsive approach works well for mixed-size cards.

### Grafana Mobile

**What it does well:**
- Responsive panel layouts
- Touch-friendly time range selector
- Kiosk mode strips all chrome
- Variable selectors work on mobile

**What it gets wrong:**
- Panels designed for desktop often overflow on mobile
- No mobile-specific navigation
- Small text in legends and axes
- No offline support
- Panel configuration requires desktop

**Relevance to Athanor:** Avoid Grafana's mistake of just shrinking desktop panels. Design mobile-specific panel sizes.

### Linear Mobile

**What it does well (best in class for mobile dashboards):**
- Bottom tab bar with 4 primary sections
- Swipe gestures for navigation between views
- Pull-to-refresh with haptic feedback
- Compact list items with smart truncation
- Keyboard shortcuts on desktop, touch on mobile -- same data, different interaction
- Excellent offline support with optimistic updates

**What it gets wrong:**
- Feature parity with desktop takes years to achieve
- Some power features only on desktop

**Relevance to Athanor:** Linear's mobile UX is the gold standard. The bottom tab bar, swipe navigation, and compact list items are all directly applicable.

### Datadog Mobile

**What it does well:**
- Overview dashboards designed for glanceability
- Push notifications for alerts with action buttons
- Metric exploration with touch-friendly zoom
- Incident management from mobile

**What it gets wrong:**
- Complex dashboards still don't render well on small screens
- Search is buried

**Relevance to Athanor:** The alert-focused mobile experience is relevant. When something is wrong, the mobile app should surface it immediately.

### Key Takeaways

1. **Bottom tab bar** is universal across well-designed mobile dashboards
2. **Card-based layouts** beat tables/grids on mobile
3. **Tap to expand** is the standard interaction for detail views
4. **Pull-to-refresh** is expected behavior
5. **Push notifications with actions** create the "app-like" feel
6. **Glanceable summaries** on the home screen, details on tap

**Sources:**
- [The Awesome Garage: Responsive HA Dashboard for Mobile/Tablet/Desktop](https://theawesomegarage.com/blog/responsive-home-assistant-dashboard-for-mobile-tablet-and-desktop)
- [Home Assistant Blog: Dashboard Chapter 1 -- Sections View](https://www.home-assistant.io/blog/2024/03/04/dashboard-chapter-1/)
- [HomeShift: 25 Home Assistant Dashboard Examples (2026)](https://joinhomeshift.com/home-assistant-dashboard-examples)

---

## 9. Capacitor / Tauri Mobile / React Native

### Do We Need a Native Wrapper?

| Requirement | PWA | Capacitor | Tauri Mobile | React Native |
|---|---|---|---|---|
| Install to home screen | Yes | Yes (App Store too) | Yes | Yes |
| Push notifications | Yes (VAPID) | Yes (native) | Limited | Yes (native) |
| Offline support | Service Worker | Service Worker + native storage | Limited | AsyncStorage |
| Background execution | Limited (iOS) | Full | Full | Full |
| Biometric auth | WebAuthn | Native biometric APIs | Native biometric APIs | Native biometric APIs |
| Bundle size overhead | 0 | ~5 MB Capacitor shell | ~2 MB Tauri shell | ~10 MB+ RN runtime |
| Development effort | 0 (already web) | Low (wrap existing app) | Medium (Rust backend) | High (rewrite) |
| App Store distribution | No (web only) | Yes | Yes | Yes |
| Maintenance burden | Low | Medium | Medium | High |

### Analysis

**Capacitor** is the only native wrapper worth considering for Athanor. It takes an existing web app (our Next.js dashboard) and wraps it in a native shell with access to native APIs. The development cost is near-zero for basic wrapping.

**Tauri Mobile** is in early development for mobile. Its desktop story is strong (Rust backend, system webview, small binaries), but mobile support is immature. The plugin ecosystem is locked to first-party only. Not recommended for mobile in 2026.

**React Native** would mean rewriting the entire dashboard. Completely wrong for this use case.

### Recommendation: PWA First, Capacitor as Escape Hatch

For a self-hosted homelab dashboard used by one person:

1. **PWA covers everything Athanor needs.** Push notifications, install to home screen, offline awareness, biometric auth via WebAuthn.
2. **Capacitor is the escape hatch if iOS push becomes unreliable.** Wrapping the PWA in Capacitor would give native push via APNs, background execution, and App Store distribution (though the last is irrelevant).
3. **Do not invest in Capacitor now.** The overhead of maintaining a native build pipeline (Xcode, Android Studio, signing certificates) is not worth it until there's a concrete problem PWA can't solve.

The one scenario where Capacitor becomes necessary: if Shaun wants reliable push notifications when the phone is not on the home network (i.e., remote access via Tailscale), and iOS's PWA push proves flaky. But that's a future problem.

**Sources:**
- [nextnative.dev: Capacitor vs React Native (2025)](https://nextnative.dev/blog/capacitor-vs-react-native)
- [DEV.to: From PWA to Native App with Capacitor](https://dev.to/okoye_ndidiamaka_5e3b7d30/from-pwa-to-native-app-how-to-turn-your-progressive-web-app-into-a-full-fledged-mobile-experience-200i)
- [DEV.to: Taking PWAs Beyond the Basics with Capacitor.js](https://dev.to/kioumars_rahimi/taking-pwas-beyond-the-basics-with-capacitorjs-build-truly-native-like-apps-using-web-tech-2ooo)
- [Slashdot: Capacitor vs Tauri Comparison (2026)](https://slashdot.org/software/comparison/Capacitor-vs-Tauri/)

---

## 10. Authentication and Security

### Threat Model for Athanor Mobile

Athanor is a personal homelab dashboard. The threat model is:
- **On LAN:** Trusted network. Authentication is nice-to-have, not essential.
- **Via Tailscale:** Trusted tunnel. Tailscale handles identity. Authentication prevents unauthorized use if the Tailscale device is compromised.
- **Via public internet:** Not planned (ADR-016 explicitly avoids exposing services publicly).

### Authentication Options

| Approach | Complexity | UX | Security | Mobile Support |
|---|---|---|---|---|
| **No auth (LAN only)** | None | Perfect | Low | Perfect |
| **Basic auth** | Minimal | Bad (re-enter constantly) | Low | Poor |
| **Cookie session with pin/password** | Low | Medium | Medium | Good |
| **WebAuthn (biometric)** | Medium | Excellent | High | Excellent |
| **Tailscale identity** | Low | Transparent | High | Good (if Tailscale installed) |

### Recommended: Layered Approach

1. **LAN access:** No authentication required. If you're on the home network, you're trusted.
2. **Tailscale access:** Use Tailscale's built-in identity headers (when using Tailscale Serve/Funnel) or simply trust that Tailscale's ACLs control who can reach the dashboard.
3. **Optional WebAuthn:** Add biometric auth as an opt-in for Shaun's phone. Face ID / fingerprint to unlock the dashboard when accessed from mobile. This prevents someone who picks up Shaun's phone from seeing the dashboard (even though the data isn't particularly sensitive).

### WebAuthn Implementation

WebAuthn is the standard for passwordless biometric authentication in the browser:

```typescript
// Registration (one-time setup)
const credential = await navigator.credentials.create({
  publicKey: {
    challenge: serverChallenge,
    rp: { name: 'Athanor', id: 'athanor.local' },
    user: {
      id: userId,
      name: 'shaun',
      displayName: 'Shaun',
    },
    pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
    authenticatorSelection: {
      authenticatorAttachment: 'platform',  // Use device biometric
      userVerification: 'required',
    },
  },
});

// Authentication (each session)
const assertion = await navigator.credentials.get({
  publicKey: {
    challenge: serverChallenge,
    rpId: 'athanor.local',
    userVerification: 'required',
  },
});
```

### Session Persistence

For mobile, the session must persist across app launches. Nobody wants to authenticate every time they open the dashboard.

- **Long-lived cookie (30 days):** Simple. Set `HttpOnly`, `SameSite=Strict`, `Secure` (if HTTPS). Auto-renewed on activity.
- **Refresh token in HttpOnly cookie + short-lived access token:** More secure but overkill for a single-user homelab.
- **Recommendation:** Single long-lived session cookie. Re-authenticate only after 30 days of inactivity or explicit logout.

### HTTPS Consideration

WebAuthn requires a secure context (HTTPS or localhost). Options for the homelab:

1. **Self-signed certificate:** Works but causes browser warnings. Needs manual trust installation on each device.
2. **mkcert (local CA):** Generates certificates trusted by your devices. Best for LAN-only.
3. **Tailscale HTTPS:** Tailscale can provision HTTPS certificates for `*.ts.net` domains. If Tailscale is deployed, this is the cleanest option.
4. **Let's Encrypt via reverse proxy:** Only works if the dashboard is exposed to the internet (not planned).

**Recommendation:** Use Tailscale HTTPS when Tailscale is deployed (ADR-016). Until then, HTTP on LAN is fine -- WebAuthn won't work without HTTPS, but basic cookie auth will.

**Sources:**
- [MDN: Web Authentication API (WebAuthn)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API)
- [Google: Build Your First WebAuthn App](https://developers.google.com/codelabs/webauthn-reauth)
- [Headscale: Self-Hosted Tailscale Control Server](https://github.com/juanfont/headscale)
- [blog.antsu.net: Authentik as Identity Provider for Tailscale](https://blog.antsu.net/custom-tailscale-oidc-provider-with-authentik/)

---

## Implementation Roadmap

### Phase 1: PWA Foundation (1 session)

1. Create `app/manifest.ts` with Athanor branding
2. Generate PWA icons (192, 512, 512-maskable, 180 apple-touch)
3. Update `app/layout.tsx` with PWA metadata and viewport
4. Create minimal `public/sw.js` (push handler + notification click)
5. Generate VAPID keys, add to `.env`
6. Verify install-to-home-screen works on iPhone and Android

### Phase 2: Mobile Layout (1-2 sessions)

1. Create `BottomNav` component (5 tabs: Home, GPUs, Agents, Chat, More)
2. Update `layout.tsx` with responsive layout (sidebar desktop, bottom nav mobile)
3. Add responsive breakpoints to all page components
4. Create mobile-specific card variants (compact GPU card, etc.)
5. Add `overscroll-behavior: contain` and pull-to-refresh
6. Ensure all touch targets are 44px minimum

### Phase 3: Push Notifications (1 session)

1. Create `app/actions.ts` with VAPID push logic
2. Create push subscription management (subscribe/unsubscribe)
3. Store subscriptions in Redis (or Qdrant)
4. Wire agent events (task complete, failure, escalation) to push
5. Wire system alerts (GPU overtemp, service down) to push
6. Test on iOS (home screen install) and Android

### Phase 4: Real-Time (1 session)

1. Create SSE endpoint at `/api/events`
2. Replace polling with SSE on dashboard home page
3. Add `visibilitychange` reconnection handler
4. Add connection status indicator (online/offline badge)
5. Keep WebSocket for chat only

### Phase 5: Polish (ongoing)

1. Add pull-to-refresh with loading indicator
2. Add haptic feedback on Android (progressive enhancement)
3. Add offline fallback page via service worker
4. Add notification action buttons (approve/reject from notification)
5. Consider Capacitor wrapper if iOS push proves unreliable
6. Add WebAuthn when Tailscale HTTPS is available

---

## Technology Stack Summary

| Layer | Technology | Status |
|---|---|---|
| Framework | Next.js 16.1.6 | Already deployed |
| UI | React 19 + shadcn/ui + Tailwind v4 | Already deployed |
| PWA | Manual service worker (`public/sw.js`) | New |
| Manifest | `app/manifest.ts` (Next.js built-in) | New |
| Push | `web-push` npm + VAPID keys | New |
| Real-time | SSE (`/api/events`) + WebSocket (chat only) | New (replaces polling) |
| Charts | Custom SVG Sparkline + Recharts (for complex) | Sparkline exists, Recharts new |
| Mobile nav | Custom BottomNav component | New |
| Auth | Long-lived cookie (LAN) + WebAuthn (future, needs HTTPS) | Future |
| Native wrapper | None (PWA). Capacitor as escape hatch. | Not needed |
| Notifications backup | ntfy on VAULT (for critical alerts) | Optional |

---

## Open Questions

1. **Icon design.** The Athanor PWA icons need to be designed. The current favicon is the Next.js default. Need a custom icon that reads well at 192x192 and works as a maskable icon.
2. **Which 5 tabs for mobile bottom nav?** Proposed: Home, GPUs, Agents, Chat, More. But "Services" and "Tasks" might be more useful than "Chat" on mobile.
3. **SSE endpoint backend.** The SSE endpoint needs a source of real-time events. Currently the dashboard polls individual service APIs. Need to decide: does the SSE endpoint poll on behalf of clients (server-side aggregation) or does it subscribe to Redis pub/sub (the GWT workspace already broadcasts there)?
4. **Notification trigger integration.** Where do push notification triggers live? In the agent framework (Node 1:9000)? In the dashboard API routes (Node 2:3001)? Or in a separate notification service?

---

## Sources Index

### PWA Capabilities
- [Brainhub: PWA on iOS (2025)](https://brainhub.eu/library/pwa-on-ios)
- [Mobiloud: PWAs on iOS (2026)](https://www.mobiloud.com/blog/progressive-web-apps-ios)
- [Progressier: PWA vs Native Comparison (2026)](https://progressier.com/pwa-vs-native-app-comparison-table)
- [ATAK Interactive: What's New in PWAs for 2025](https://www.atakinteractive.com/blog/whats-new-in-pwas-for-2025)

### Next.js PWA
- [Next.js Official: PWA Guide](https://nextjs.org/docs/app/guides/progressive-web-apps)
- [Serwist: Getting Started](https://serwist.pages.dev/docs/next/getting-started)
- [Serwist: Caching Strategies](https://serwist.pages.dev/docs/serwist/runtime-caching/caching-strategies)
- [LogRocket: Next.js 16 PWA with Offline Support](https://blog.logrocket.com/nextjs-16-pwa-offline-support/)

### Mobile Design
- [Toptal: Mobile Dashboard UI Best Practices](https://www.toptal.com/designers/dashboard-design/mobile-dashboard-ui)
- [Medium: 20 Dashboard UX Principles (2025)](https://medium.com/@allclonescript/20-best-dashboard-ui-ux-design-principles-you-need-in-2025-30b661f2f795)
- [brand.dev: Dashboard Design Best Practices](https://www.brand.dev/blog/dashboard-design-best-practices)

### Touch & Haptics
- [CodeByUmar: Vibration API (2025)](https://codebyumar.medium.com/how-to-use-the-vibration-api-to-add-haptic-feedback-to-mobile-web-apps-734dea37dc8f)
- [react-haptic](https://github.com/ryotanakata/react-haptic)
- [OpenReplay: Haptic Feedback for Web Apps](https://blog.openreplay.com/haptic-feedback-for-web-apps-with-the-vibration-api/)

### Push Notifications
- [Isala Piyarisi: Web Push Without Firebase](https://isala.me/blog/web-push-notifications-without-firebase/)
- [MagicBell: Push Notifications in PWAs](https://www.magicbell.com/blog/using-push-notifications-in-pwas)
- [ntfy.sh](https://ntfy.sh/)

### Real-Time
- [codebyte.solutions: HTTPS vs WebSockets vs SSE](https://www.codebyte.solutions/https-vs-websockets-vs-sse-a-simple-guide-for-mobile-apps/)
- [portalZINE: SSE in 2025](https://portalzine.de/sses-glorious-comeback-why-2025-is-the-year-of-server-sent-events/)
- [SoftwareMill: SSE vs WebSockets](https://softwaremill.com/sse-vs-websockets-comparing-real-time-communication-protocols/)

### Charts
- [LogRocket: React Chart Libraries (2025)](https://blog.logrocket.com/best-react-chart-libraries-2025/)
- [Tremor: SparkChart](https://www.tremor.so/docs/visualizations/spark-chart)
- [shadcn/ui Charts Discussion](https://github.com/shadcn-ui/ui/discussions/4133)

### Native Wrappers
- [nextnative.dev: Capacitor vs React Native](https://nextnative.dev/blog/capacitor-vs-react-native)
- [DEV.to: PWA to Native with Capacitor](https://dev.to/okoye_ndidiamaka_5e3b7d30/from-pwa-to-native-app-how-to-turn-your-progressive-web-app-into-a-full-fledged-mobile-experience-200i)
- [Slashdot: Capacitor vs Tauri (2026)](https://slashdot.org/software/comparison/Capacitor-vs-Tauri/)

### Auth & Security
- [MDN: Web Authentication API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API)
- [Google: WebAuthn Codelab](https://developers.google.com/codelabs/webauthn-reauth)
- [Headscale (self-hosted Tailscale)](https://github.com/juanfont/headscale)

### Mobile Dashboard Examples
- [The Awesome Garage: Responsive HA Dashboard](https://theawesomegarage.com/blog/responsive-home-assistant-dashboard-for-mobile-tablet-and-desktop)
- [Home Assistant: Dashboard Chapter 1](https://www.home-assistant.io/blog/2024/03/04/dashboard-chapter-1/)
- [shadcn/ui: Bottom Navigation Feature Request](https://github.com/shadcn-ui/ui/issues/8847)
