"use client";

import { useEffect, useRef, useState } from "react";

export interface GpuSnapshot {
  index: number;
  name: string;
  node: string;
  utilization: number;
  temperature: number;
  memUsedGB: number;
  memTotalGB: number;
  power: number;
  workload: string;
}

export interface SystemSnapshot {
  gpus: GpuSnapshot[];
  agents: { online: boolean; count: number; names: string[] };
  services: { up: number; total: number; down: string[] };
  tasks: {
    total: number;
    by_status: { completed: number; running: number; failed: number; pending: number };
    currently_running: number;
    worker_running: boolean;
  } | null;
  media: { streamCount: number; downloadCount: number; sessions: { title: string; state: string }[] } | null;
  timestamp: string;
}

export function useSystemStream() {
  const [data, setData] = useState<SystemSnapshot | null>(null);
  const [connected, setConnected] = useState(false);
  const retryCount = useRef(0);

  useEffect(() => {
    let es: EventSource | null = null;
    let timeout: ReturnType<typeof setTimeout>;

    function connect() {
      es = new EventSource("/api/stream");

      es.onopen = () => {
        setConnected(true);
        retryCount.current = 0;
      };

      es.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (!parsed.error) {
            setData(parsed);
          }
        } catch { /* ignore malformed */ }
      };

      es.onerror = () => {
        setConnected(false);
        es?.close();
        // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
        const delay = Math.min(1000 * Math.pow(2, retryCount.current), 30000);
        retryCount.current++;
        timeout = setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      es?.close();
      clearTimeout(timeout);
    };
  }, []);

  return { data, connected };
}
