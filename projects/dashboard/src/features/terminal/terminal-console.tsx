"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";

const TerminalView = dynamic(() => import("@/components/terminal-view"), {
  ssr: false,
  loading: () => (
    <div className="flex h-96 items-center justify-center rounded-2xl border border-border/70 bg-background/20">
      <p className="text-sm text-muted-foreground">Loading terminal...</p>
    </div>
  ),
});

const NODES = [
  { id: "dev", label: "DEV", host: "DEV" },
  { id: "foundry", label: "Foundry", host: "FOUNDRY" },
  { id: "workshop", label: "Workshop", host: "WORKSHOP" },
];

type BridgeAccess = {
  bridgeUrl: string;
  authMode: "required" | "optional";
  ticket: string | null;
  expiresAt: string | null;
  allowedNodes: string[];
  bridgeReachable?: boolean;
};

export function TerminalConsole() {
  const operatorSession = useOperatorSessionStatus();
  const sessionLocked = isOperatorSessionLocked(operatorSession);
  const [selectedNode, setSelectedNode] = useState(NODES[0]);
  const [connected, setConnected] = useState(false);
  const [bridgeAccess, setBridgeAccess] = useState<BridgeAccess | null>(null);
  const [bridgeError, setBridgeError] = useState<string | null>(null);
  const [loadingBridgeAccess, setLoadingBridgeAccess] = useState(true);

  useEffect(() => {
    let cancelled = false;

    if (operatorSession.isPending) {
      setLoadingBridgeAccess(true);
      return () => {
        cancelled = true;
      };
    }

    if (sessionLocked) {
      setLoadingBridgeAccess(false);
      setBridgeAccess(null);
      setBridgeError("Operator session required. Unlock the operator session before opening the terminal.");
      setConnected(false);
      return () => {
        cancelled = true;
      };
    }

    async function loadBridgeAccess() {
      setLoadingBridgeAccess(true);
      setBridgeError(null);
      setConnected(false);

      try {
        const response = await fetch("/api/operator/terminal-bridge", {
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "x-athanor-request-origin": window.location.origin,
          },
        });

        const payload = (await response.json().catch(() => ({}))) as Partial<BridgeAccess> & {
          error?: string;
        };
        if (cancelled) {
          return;
        }

        if (!response.ok) {
          setBridgeAccess(null);
          setBridgeError(
            payload.error ||
              (response.status === 403
                ? "Operator session required. Unlock the operator session before opening the terminal."
                : "Terminal bridge access is unavailable.")
          );
          return;
        }

        const allowedNodes = payload.allowedNodes?.length
          ? NODES.filter((node) => payload.allowedNodes?.includes(node.id))
          : NODES;
        if (payload.bridgeReachable === false) {
          setBridgeAccess(null);
          setBridgeError("Terminal bridge is configured but currently unreachable.");
          if (!allowedNodes.find((node) => node.id === selectedNode.id)) {
            setSelectedNode(allowedNodes[0] ?? NODES[0]);
          }
          return;
        }

        const nextAccess: BridgeAccess = {
          bridgeUrl: payload.bridgeUrl || "",
          authMode: payload.authMode === "required" ? "required" : "optional",
          ticket: typeof payload.ticket === "string" ? payload.ticket : null,
          expiresAt: typeof payload.expiresAt === "string" ? payload.expiresAt : null,
          allowedNodes: allowedNodes.map((node) => node.id),
          bridgeReachable: payload.bridgeReachable ?? true,
        };
        setBridgeAccess(nextAccess);

        if (!allowedNodes.find((node) => node.id === selectedNode.id)) {
          setSelectedNode(allowedNodes[0] ?? NODES[0]);
        }
      } catch {
        if (!cancelled) {
          setBridgeAccess(null);
          setBridgeError("Terminal bridge access could not be loaded.");
        }
      } finally {
        if (!cancelled) {
          setLoadingBridgeAccess(false);
        }
      }
    }

    void loadBridgeAccess();
    return () => {
      cancelled = true;
    };
  }, [operatorSession.isPending, sessionLocked]);

  const availableNodes =
    bridgeAccess?.allowedNodes.length
      ? NODES.filter((node) => bridgeAccess.allowedNodes.includes(node.id))
      : NODES;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Utility Console"
        title="Terminal"
        description="Operator escape hatch for direct system access with shell-consistent framing and connection state."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card className="border-border/70 bg-card/70 xl:col-span-2">
            <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="text-sm font-medium">Active node</p>
                <p className="text-sm text-muted-foreground">{selectedNode.label}</p>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant={connected ? "secondary" : "outline"}>
                  {connected ? "Connected" : loadingBridgeAccess ? "Loading access" : "Disconnected"}
                </Badge>
                <label htmlFor="terminal-node-selector" className="sr-only">
                  Active node
                </label>
                <select
                  id="terminal-node-selector"
                  aria-label="Active node"
                  value={selectedNode.id}
                  disabled={!bridgeAccess || availableNodes.length === 0}
                  onChange={(event) => {
                    const nextNode = availableNodes.find((node) => node.id === event.target.value);
                    if (nextNode) {
                      setSelectedNode(nextNode);
                    }
                  }}
                  className="rounded-xl border border-border/70 bg-background/30 px-3 py-2 text-sm"
                >
                  {availableNodes.map((node) => (
                    <option key={node.id} value={node.id}>
                      {node.label}
                    </option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>
        </div>
      </PageHeader>

      <Card className="border-border/70 bg-card/70">
        <CardHeader>
          <CardTitle className="text-lg">
            {selectedNode.label} ({selectedNode.host})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-3">
          {bridgeAccess ? (
            <TerminalView
              nodeId={selectedNode.id}
              host={selectedNode.host}
              bridgeUrl={bridgeAccess.bridgeUrl}
              bridgeTicket={bridgeAccess.ticket}
              onConnectionChange={setConnected}
            />
          ) : (
            <div className="flex h-96 items-center justify-center rounded-md border border-dashed border-border/70 bg-background/20 px-6 text-center text-sm text-muted-foreground">
              {bridgeError ||
                "Operator terminal access is unavailable until the terminal bridge and operator session are ready."}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
