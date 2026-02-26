"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

interface ApprovalCardProps {
  notificationId: string;
  agent: string;
  action: string;
  detail?: string;
}

export function ApprovalCard({ notificationId, agent, action, detail }: ApprovalCardProps) {
  const [resolved, setResolved] = useState<"approved" | "rejected" | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleResolve(decision: "approved" | "rejected") {
    setLoading(true);
    try {
      const res = await fetch(`/api/agents/proxy?path=/v1/notifications/${notificationId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolution: decision }),
      });
      if (res.ok) {
        setResolved(decision);
      }
    } catch {
      // Silently fail — notification may not exist
    } finally {
      setLoading(false);
    }
  }

  if (resolved) {
    return (
      <div className="my-2 rounded-md border border-border bg-card px-3 py-2">
        <span className="text-xs text-muted-foreground">
          {resolved === "approved" ? "Approved" : "Rejected"}: {action}
        </span>
      </div>
    );
  }

  return (
    <div className="my-2 rounded-md border border-border bg-card p-3 space-y-2">
      <div>
        <span className="text-xs font-medium text-primary">{agent}</span>
        <span className="text-xs text-muted-foreground"> wants to </span>
        <span className="text-xs font-medium">{action}</span>
      </div>
      {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() => handleResolve("approved")}
          disabled={loading}
          className="h-7 text-xs"
        >
          Approve
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => handleResolve("rejected")}
          disabled={loading}
          className="h-7 text-xs"
        >
          Reject
        </Button>
      </div>
    </div>
  );
}
