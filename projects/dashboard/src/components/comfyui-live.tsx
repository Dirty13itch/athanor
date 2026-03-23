"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ImageIcon, Loader2, Clock, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface QueueItem {
  prompt_id: string;
  number: number;
}

interface GenerationProgress {
  promptId: string;
  node: string;
  value: number;
  max: number;
}

export function ComfyUILivePanel() {
  const [wsConnected, setWsConnected] = useState(false);
  const [progress, setProgress] = useState<GenerationProgress | null>(null);
  const [lastImage, setLastImage] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Poll queue status via REST
  const { data: queueData } = useQuery({
    queryKey: ["comfyui-queue"],
    queryFn: () => fetch("/api/comfyui/stats").then((r) => r.json()),
    refetchInterval: 10_000,
  });

  // WebSocket for real-time progress
  useEffect(() => {
    const ws = new WebSocket("ws://192.168.1.225:8188/ws");

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => {
      setWsConnected(false);
      setProgress(null);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "progress") {
          setProgress({
            promptId: msg.data?.prompt_id || "",
            node: msg.data?.node || "",
            value: msg.data?.value || 0,
            max: msg.data?.max || 1,
          });
        }
        if (msg.type === "executed") {
          setProgress(null);
          // Check for output images
          const outputs = msg.data?.output;
          if (outputs?.images?.[0]) {
            const img = outputs.images[0];
            setLastImage(`http://192.168.1.225:8188/view?filename=${img.filename}&subfolder=${img.subfolder || ""}&type=${img.type || "output"}`);
          }
        }
        if (msg.type === "execution_start") {
          setProgress({ promptId: msg.data?.prompt_id || "", node: "starting", value: 0, max: 1 });
        }
        if (msg.type === "execution_complete") {
          setProgress(null);
        }
      } catch {
        // ignore malformed messages
      }
    };

    wsRef.current = ws;
    return () => ws.close();
  }, []);

  const queueRunning = queueData?.queueRunning ?? 0;
  const queuePending = queueData?.queuePending ?? 0;
  const deviceName = queueData?.deviceName ?? "Unknown";
  const vramUsed = queueData?.vramUsedGiB ?? 0;
  const vramTotal = queueData?.vramTotalGiB ?? 0;
  const pct = progress ? Math.round((progress.value / progress.max) * 100) : 0;

  return (
    <Card className="surface-panel">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <ImageIcon className="h-4 w-4 text-primary" />
            ComfyUI Generation
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-0.5">
            {deviceName ? deviceName.split(":")[0]?.trim()?.split(" ").slice(-3).join(" ") : "GPU"} · {vramUsed.toFixed(1)}/{vramTotal.toFixed(1)} GiB
          </p>
        </div>
        <Badge variant={wsConnected ? "secondary" : "outline"} className="text-[10px]">
          {wsConnected ? "Live" : "Disconnected"}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1.5">
            {queueRunning > 0 ? <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" /> : <Clock className="h-3.5 w-3.5 text-muted-foreground" />}
            <span>{queueRunning} running</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Zap className="h-3.5 w-3.5 text-muted-foreground" />
            <span>{queuePending} pending</span>
          </div>
        </div>

        {progress && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Generating: {progress.node}</span>
              <span>{pct}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-background/60 overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )}

        {lastImage && (
          <div className="rounded-xl overflow-hidden border border-border/40">
            <img src={lastImage} alt="Last generation" className="w-full h-auto" loading="lazy" />
          </div>
        )}

        {!progress && !lastImage && queueRunning === 0 && (
          <p className="text-xs text-muted-foreground text-center py-2">No active generation. Queue is idle.</p>
        )}
      </CardContent>
    </Card>
  );
}
