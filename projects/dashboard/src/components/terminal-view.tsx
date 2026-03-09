"use client";

import { useEffect, useEffectEvent, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import "@xterm/xterm/css/xterm.css";

interface TerminalViewProps {
  nodeId: string;
  host: string;
  onConnectionChange: (connected: boolean) => void;
}

export default function TerminalView({
  nodeId,
  host,
  onConnectionChange,
}: TerminalViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const [error, setError] = useState<string | null>(null);

  const connect = useEffectEvent(() => {
    if (!containerRef.current) return;

    // Clean up previous
    wsRef.current?.close();
    termRef.current?.dispose();

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace",
      theme: {
        background: "#09090b",
        foreground: "#fafafa",
        cursor: "#fafafa",
        selectionBackground: "#27272a",
        black: "#09090b",
        red: "#ef4444",
        green: "#22c55e",
        yellow: "#eab308",
        blue: "#3b82f6",
        magenta: "#a855f7",
        cyan: "#06b6d4",
        white: "#fafafa",
        brightBlack: "#52525b",
        brightRed: "#f87171",
        brightGreen: "#4ade80",
        brightYellow: "#facc15",
        brightBlue: "#60a5fa",
        brightMagenta: "#c084fc",
        brightCyan: "#22d3ee",
        brightWhite: "#ffffff",
      },
    });

    const fit = new FitAddon();
    const links = new WebLinksAddon();
    term.loadAddon(fit);
    term.loadAddon(links);
    term.open(containerRef.current);
    fit.fit();

    termRef.current = term;
    fitRef.current = fit;

    // WebSocket connection to PTY bridge
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProtocol}//${window.location.hostname}:3100/ws?node=${nodeId}`;

    term.writeln(`\x1b[90mConnecting to ${host}...\x1b[0m`);
    setError(null);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        onConnectionChange(true);
        setError(null);
        // Send terminal size
        ws.send(JSON.stringify({
          type: "resize",
          cols: term.cols,
          rows: term.rows,
        }));
      };

      ws.onmessage = (event) => {
        term.write(event.data);
      };

      ws.onclose = () => {
        onConnectionChange(false);
        term.writeln("\r\n\x1b[90mConnection closed.\x1b[0m");
      };

      ws.onerror = () => {
        onConnectionChange(false);
        setError("WebSocket connection failed. Terminal bridge may not be running.");
        term.writeln("\r\n\x1b[31mConnection failed.\x1b[0m");
        term.writeln("\x1b[90mThe terminal bridge (ws-pty) needs to be running on port 3100.\x1b[0m");
        term.writeln("\x1b[90mSee docs/decisions/ADR-020-interaction-architecture.md for setup.\x1b[0m");
      };

      // Forward user input to WebSocket
      term.onData((data) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(data);
        }
      });

      // Forward resize events
      term.onResize(({ cols, rows }) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "resize", cols, rows }));
        }
      });
    } catch {
      setError("Failed to create WebSocket connection.");
      term.writeln("\r\n\x1b[31mFailed to connect.\x1b[0m");
    }

    return term;
  });

  useEffect(() => {
    const term = connect();

    // Handle window resize
    const handleResize = () => {
      fitRef.current?.fit();
    };
    window.addEventListener("resize", handleResize);

    // Handle container resize with ResizeObserver
    const observer = new ResizeObserver(() => {
      fitRef.current?.fit();
    });
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => {
      window.removeEventListener("resize", handleResize);
      observer.disconnect();
      wsRef.current?.close();
      term?.dispose();
    };
  }, [host, nodeId]);

  return (
    <div className="relative h-full">
      <div
        ref={containerRef}
        className="h-full w-full rounded-md bg-[#09090b]"
      />
      {error && (
        <div className="absolute inset-x-0 bottom-0 rounded-b-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </div>
      )}
    </div>
  );
}
