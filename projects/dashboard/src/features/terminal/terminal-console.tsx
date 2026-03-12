"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const TerminalView = dynamic(() => import("@/components/terminal-view"), {
  ssr: false,
  loading: () => (
    <div className="flex h-96 items-center justify-center rounded-2xl border border-border/70 bg-background/20">
      <p className="text-sm text-muted-foreground">Loading terminal...</p>
    </div>
  ),
});

const NODES = [
  { id: "dev", label: "DEV", host: "dev" },
  { id: "node1", label: "Foundry", host: "node1" },
  { id: "node2", label: "Workshop", host: "node2" },
];

export function TerminalConsole() {
  const [selectedNode, setSelectedNode] = useState(NODES[0]);
  const [connected, setConnected] = useState(false);

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
                <Badge variant={connected ? "secondary" : "outline"}>{connected ? "Connected" : "Disconnected"}</Badge>
                <label htmlFor="terminal-node-selector" className="sr-only">
                  Active node
                </label>
                <select
                  id="terminal-node-selector"
                  aria-label="Active node"
                  value={selectedNode.id}
                  onChange={(event) => {
                    const nextNode = NODES.find((node) => node.id === event.target.value);
                    if (nextNode) {
                      setSelectedNode(nextNode);
                    }
                  }}
                  className="rounded-xl border border-border/70 bg-background/30 px-3 py-2 text-sm"
                >
                  {NODES.map((node) => (
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
          <TerminalView nodeId={selectedNode.id} host={selectedNode.host} onConnectionChange={setConnected} />
        </CardContent>
      </Card>
    </div>
  );
}
