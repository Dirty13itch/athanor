"use client";

import { useEffect, useRef } from "react";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";

const HEARTBEAT_INTERVAL_MS = 45_000;
const MIN_REPEAT_INTERVAL_MS = 10_000;

type HeartbeatState = "at_desk" | "away";

function postHeartbeat(state: HeartbeatState, reason: string) {
  const body = JSON.stringify({
    state,
    actor: "dashboard-heartbeat",
    source: "dashboard_heartbeat",
    reason,
  });

  if (state === "away" && typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
    const beaconBody = new Blob([body], { type: "application/json" });
    if (navigator.sendBeacon("/api/governor/heartbeat", beaconBody)) {
      return;
    }
  }

  void fetch("/api/governor/heartbeat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    cache: "no-store",
    keepalive: true,
  });
}

export function OperatorPresenceHeartbeat() {
  const session = useOperatorSessionStatus();
  const lastSentRef = useRef<{ state: HeartbeatState | null; timestamp: number }>({
    state: null,
    timestamp: 0,
  });

  useEffect(() => {
    if (!session.isFetched || isOperatorSessionLocked(session)) {
      return;
    }

    let intervalId: number | null = null;

    const send = (state: HeartbeatState, reason: string, force = false) => {
      const now = Date.now();
      if (
        !force &&
        lastSentRef.current.state === state &&
        now - lastSentRef.current.timestamp < MIN_REPEAT_INTERVAL_MS
      ) {
        return;
      }
      lastSentRef.current = { state, timestamp: now };
      postHeartbeat(state, reason);
    };

    const currentState = (): HeartbeatState => (document.hidden ? "away" : "at_desk");

    const restartInterval = () => {
      if (intervalId !== null) {
        window.clearInterval(intervalId);
        intervalId = null;
      }
      if (!document.hidden) {
        intervalId = window.setInterval(() => {
          send("at_desk", "Visible dashboard heartbeat");
        }, HEARTBEAT_INTERVAL_MS);
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        send("away", "Dashboard hidden; operator marked away.", true);
      } else {
        send("at_desk", "Dashboard visible heartbeat.", true);
      }
      restartInterval();
    };

    const handlePageHide = () => {
      send("away", "Dashboard page hidden or unloading.", true);
    };

    send(
      currentState(),
      document.hidden ? "Dashboard loaded in background." : "Dashboard mounted and visible.",
      true
    );
    restartInterval();

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("pagehide", handlePageHide);

    return () => {
      if (intervalId !== null) {
        window.clearInterval(intervalId);
      }
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("pagehide", handlePageHide);
    };
  }, [session.isFetched, session.requiresSession, session.unlocked]);

  return null;
}
