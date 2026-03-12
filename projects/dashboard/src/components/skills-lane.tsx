"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Brain, RefreshCcw } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  asArray,
  asObject,
  fetchJson,
  getNumber,
  getString,
  type JsonObject,
} from "@/components/runtime-panel-utils";

export function SkillsLane() {
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const skillsQuery = useQuery({
    queryKey: ["operator-panel", "skills-lane"],
    queryFn: async () => ({
      stats: await fetchJson<JsonObject>("/api/skills/stats"),
      top: await fetchJson<JsonObject>("/api/skills/top?limit=5"),
      skills: await fetchJson<JsonObject>("/api/skills?limit=8"),
    }),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const topSkills = asArray<JsonObject>(asObject(skillsQuery.data?.top)?.skills);
  const skillList = asArray<JsonObject>(asObject(skillsQuery.data?.skills)?.skills);

  useEffect(() => {
    if (!selectedSkillId && skillList.length > 0) {
      setSelectedSkillId(getString(skillList[0].skill_id));
    }
  }, [selectedSkillId, skillList]);

  const skillDetailQuery = useQuery({
    queryKey: ["operator-panel", "skill-detail", selectedSkillId],
    enabled: Boolean(selectedSkillId),
    queryFn: async () => fetchJson<JsonObject>(`/api/skills/${selectedSkillId}`),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  async function recordExecution(success: boolean) {
    if (!selectedSkillId) {
      return;
    }
    setBusy(true);
    setFeedback(null);
    try {
      await fetchJson<JsonObject>(`/api/skills/${selectedSkillId}/execution`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          success,
          duration_ms: success ? 780 : 1460,
          context: { source: "dashboard_skills_lane", operator_marked: true },
        }),
      });
      setFeedback(success ? "Recorded a successful execution." : "Recorded a failed execution.");
      await Promise.all([skillsQuery.refetch(), skillDetailQuery.refetch()]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to record skill execution.");
    } finally {
      setBusy(false);
    }
  }

  if (skillsQuery.isError && !skillsQuery.data) {
    return (
      <ErrorPanel
        title="Skills lane"
        description={
          skillsQuery.error instanceof Error
            ? skillsQuery.error.message
            : "Failed to load skills data."
        }
      />
    );
  }

  const stats = asObject(skillsQuery.data?.stats);
  const selectedSkill = asObject(skillDetailQuery.data);
  const selectedTags = useMemo(() => asArray<string>(selectedSkill?.tags).slice(0, 5), [selectedSkill]);

  return (
    <Card className="border-border/70 bg-card/70">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Brain className="h-5 w-5 text-primary" />
          Skills lane
        </CardTitle>
        <CardDescription>
          Proven operator skills, success telemetry, and quick runtime verification.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {feedback ? (
          <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-4">
          <Metric label="Total skills" value={`${getNumber(stats?.total, 0)}`} />
          <Metric label="Executed" value={`${getNumber(stats?.executed, 0)}`} />
          <Metric
            label="Success rate"
            value={`${Math.round(getNumber(stats?.avg_success_rate, 0) * 100)}%`}
          />
          <Metric label="Categories" value={`${getNumber(stats?.categories, 0)}`} />
        </div>

        <div className="grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Top skills</p>
            {topSkills.length > 0 ? (
              topSkills.map((skill) => {
                const skillId = getString(skill.skill_id);
                const active = selectedSkillId === skillId;
                return (
                  <button
                    key={skillId}
                    type="button"
                    onClick={() => setSelectedSkillId(skillId)}
                    className={`w-full rounded-xl border px-3 py-3 text-left transition ${
                      active
                        ? "border-primary/60 bg-primary/10"
                        : "border-border/60 bg-background/30 hover:bg-accent"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{getString(skill.name)}</p>
                        <p className="text-xs text-muted-foreground">
                          {getString(skill.category, "general")}
                        </p>
                      </div>
                      <Badge variant="outline">
                        {Math.round(getNumber(skill.success_rate, 0) * 100)}%
                      </Badge>
                    </div>
                  </button>
                );
              })
            ) : (
              <EmptyState
                title="No skills returned"
                description="The runtime has not surfaced any learned skills yet."
                className="py-8"
              />
            )}
          </div>

          <div className="rounded-xl border border-border/60 bg-background/30 p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Skill detail
              </p>
              <Button variant="outline" size="sm" onClick={() => void skillsQuery.refetch()} disabled={skillsQuery.isFetching}>
                <RefreshCcw className={`mr-2 h-4 w-4 ${skillsQuery.isFetching ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
            {selectedSkill ? (
              <div className="mt-3 space-y-3 text-sm">
                <div>
                  <p className="font-medium">{getString(selectedSkill.name)}</p>
                  <p className="mt-1 text-muted-foreground">
                    {getString(selectedSkill.description, "No description recorded.")}
                  </p>
                </div>
                <div className="grid gap-2 sm:grid-cols-3">
                  <Metric
                    label="Executions"
                    value={`${getNumber(selectedSkill.execution_count, 0)}`}
                  />
                  <Metric
                    label="Success"
                    value={`${Math.round(getNumber(selectedSkill.success_rate, 0) * 100)}%`}
                  />
                  <Metric
                    label="Avg ms"
                    value={`${Math.round(getNumber(selectedSkill.avg_duration_ms, 0))}`}
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedTags.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <RuntimeList
                    title="Trigger conditions"
                    items={asArray<string>(selectedSkill.trigger_conditions)}
                  />
                  <RuntimeList title="Steps" items={asArray<string>(selectedSkill.steps)} />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => void recordExecution(true)} disabled={busy}>
                    Mark success
                  </Button>
                  <Button variant="outline" onClick={() => void recordExecution(false)} disabled={busy}>
                    Mark failure
                  </Button>
                </div>
              </div>
            ) : skillDetailQuery.isLoading ? (
              <p className="mt-3 text-sm text-muted-foreground">Loading skill detail...</p>
            ) : (
              <EmptyState
                title="Choose a skill"
                description="Select a skill to inspect trigger conditions and outcomes."
                className="py-10"
              />
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/40 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}

function RuntimeList({ title, items }: { title: string; items: string[] }) {
  const visibleItems = useMemo(() => items.filter(Boolean), [items]);
  return (
    <div className="rounded-xl border border-border/60 bg-background/40 p-3">
      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{title}</p>
      {visibleItems.length > 0 ? (
        <ul className="mt-2 space-y-2 text-sm text-muted-foreground">
          {visibleItems.slice(0, 5).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">No entries recorded.</p>
      )}
    </div>
  );
}
