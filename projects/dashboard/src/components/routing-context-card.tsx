"use client";

import { useState } from "react";
import { Network, Sparkles } from "lucide-react";
import { ErrorPanel } from "@/components/error-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  fetchJson,
  getBoolean,
  getNumber,
  getString,
  type JsonObject,
} from "@/components/runtime-panel-utils";

const AGENT_OPTIONS = [
  "general-assistant",
  "research-agent",
  "coding-agent",
  "knowledge-agent",
  "media-agent",
  "home-agent",
];

export function RoutingContextCard({
  title = "Routing and context preview",
  description = "Preview injected context and model-routing decisions before dispatch.",
  defaultAgent = "general-assistant",
  defaultPrompt = "Summarize the current Athanor runtime posture and call out the top risk.",
}: {
  title?: string;
  description?: string;
  defaultAgent?: string;
  defaultPrompt?: string;
}) {
  const [agent, setAgent] = useState(defaultAgent);
  const [prompt, setPrompt] = useState(defaultPrompt);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [contextPreview, setContextPreview] = useState<JsonObject | null>(null);
  const [classification, setClassification] = useState<JsonObject | null>(null);

  async function runPreview() {
    if (!prompt.trim()) {
      return;
    }
    setBusy(true);
    setFeedback(null);
    try {
      const [nextContext, nextRouting] = await Promise.all([
        fetchJson<JsonObject>("/api/context/preview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ agent, message: prompt.trim() }),
        }),
        fetchJson<JsonObject>("/api/routing/classify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ agent, prompt: prompt.trim(), conversation_length: 1 }),
        }),
      ]);
      setContextPreview(nextContext);
      setClassification(nextRouting);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Routing preview failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="surface-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Network className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {feedback ? <ErrorPanel title="Routing preview" description={feedback} /> : null}

        <div className="grid gap-3 md:grid-cols-[12rem_1fr]">
          <label className="space-y-2 text-sm">
            <span className="font-medium">Agent</span>
            <select
              value={agent}
              onChange={(event) => setAgent(event.target.value)}
              className="surface-instrument w-full rounded-xl border px-3 py-2 text-sm outline-none transition focus:border-primary"
            >
              {AGENT_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2 text-sm">
            <span className="font-medium">Prompt</span>
            <textarea
              rows={3}
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              className="surface-instrument w-full rounded-xl border px-3 py-2 text-sm outline-none transition focus:border-primary"
            />
          </label>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button onClick={() => void runPreview()} disabled={busy || !prompt.trim()}>
            <Sparkles className="mr-2 h-4 w-4" />
            {busy ? "Running..." : "Preview"}
          </Button>
        </div>

        {(classification || contextPreview) && (
          <div className="grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="surface-instrument rounded-xl border p-3 text-sm">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Route classification
              </p>
              {classification ? (
                <div className="mt-3 space-y-2">
                  <MetricRow label="Tier" value={getString(classification.tier)} />
                  <MetricRow label="Task type" value={getString(classification.task_type)} />
                  <MetricRow label="Model" value={getString(classification.model)} />
                  <MetricRow
                    label="Use agent"
                    value={getBoolean(classification.use_agent) ? "yes" : "no"}
                  />
                  <MetricRow
                    label="Confidence"
                    value={`${Math.round(getNumber(classification.confidence, 0) * 100)}%`}
                  />
                  <p className="pt-1 text-xs text-muted-foreground">
                    {getString(classification.reason, "No routing rationale returned.")}
                  </p>
                </div>
              ) : null}
            </div>

            <div className="surface-instrument rounded-xl border p-3 text-sm">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Context preview
              </p>
              {contextPreview ? (
                <>
                  <div className="mt-3 grid gap-2 sm:grid-cols-3">
                    <Metric label="Chars" value={`${getNumber(contextPreview.context_chars, 0)}`} />
                    <Metric
                      label="Tokens est"
                      value={`${getNumber(contextPreview.context_tokens_est, 0)}`}
                    />
                    <Metric label="Latency" value={`${getNumber(contextPreview.duration_ms, 0)}ms`} />
                  </div>
                  <pre className="surface-tile mt-3 max-h-56 overflow-y-auto whitespace-pre-wrap rounded-xl border p-3 text-xs text-muted-foreground">
                    {getString(contextPreview.context, "No context returned.")}
                  </pre>
                </>
              ) : null}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-metric rounded-xl border px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
