"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const TerminalView = dynamic(() => import("@/components/terminal-view"), {
  ssr: false,
  loading: () => (
    <div className="flex h-96 items-center justify-center bg-black rounded-lg">
      <p className="text-sm text-zinc-500">Loading terminal...</p>
    </div>
  ),
});

const NODES = [
  { id: "dev", label: "DEV", host: "localhost" },
  { id: "node1", label: "Foundry", host: "node1" },
  { id: "node2", label: "Workshop", host: "node2" },
];

export default function TerminalPage() {
  const [selectedNode, setSelectedNode] = useState(NODES[0]);
  const [isConnected, setIsConnected] = useState(false);

  return (
    <div className="flex h-[calc(100vh-5rem)] flex-col space-y-3 md:h-[calc(100vh-3rem)] md:space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold tracking-tight md:text-2xl">Terminal</h1>
          <p className="text-xs text-muted-foreground md:text-sm">
            Layer 5 escape hatch — direct system access
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={isConnected ? "default" : "outline"} className="text-xs">
            {isConnected ? "Connected" : "Disconnected"}
          </Badge>
          <select
            value={selectedNode.id}
            onChange={(e) => {
              const node = NODES.find((n) => n.id === e.target.value);
              if (node) setSelectedNode(node);
            }}
            className="rounded-md border border-border bg-background px-2 py-1.5 text-xs md:px-3 md:text-sm"
          >
            {NODES.map((n) => (
              <option key={n.id} value={n.id}>
                {n.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <Card className="flex flex-1 flex-col overflow-hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">
            {selectedNode.label} ({selectedNode.host})
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden p-2">
          <TerminalView
            nodeId={selectedNode.id}
            host={selectedNode.host}
            onConnectionChange={setIsConnected}
          />
        </CardContent>
      </Card>
    </div>
  );
}
