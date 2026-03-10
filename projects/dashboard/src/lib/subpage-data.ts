import { z } from "zod";
import {
  type GallerySnapshot,
  gallerySnapshotSchema,
  type HistorySnapshot,
  historySnapshotSchema,
  type HomeSnapshot,
  homeSnapshotSchema,
  type IntelligenceSnapshot,
  intelligenceSnapshotSchema,
  type MediaSnapshot,
  mediaSnapshotSchema,
  type MemorySnapshot,
  memorySnapshotSchema,
  type MonitoringSnapshot,
  monitoringSnapshotSchema,
} from "@/lib/contracts";
import { config, joinUrl } from "@/lib/config";
import {
  getFixtureGallerySnapshot,
  getFixtureHistorySnapshot,
  getFixtureHomeSnapshot,
  getFixtureIntelligenceSnapshot,
  getFixtureMediaSnapshot,
  getFixtureMemorySnapshot,
  getFixtureMonitoringSnapshot,
  isDashboardFixtureMode,
} from "@/lib/dashboard-fixtures";
import { average } from "@/lib/format";
import { getProjectsSnapshot, getWorkforceSnapshot } from "@/lib/dashboard-data";
import { getNeo4jAuthHeader } from "@/lib/server-config";

const rawActivityResponseSchema = z.object({
  activity: z
    .array(
      z.object({
        agent: z.string(),
        action_type: z.string(),
        input_summary: z.string(),
        output_summary: z.string().nullable().optional(),
        tools_used: z.array(z.string()).default([]),
        duration_ms: z.number().nullable().optional(),
        timestamp: z.string(),
      })
    )
    .default([]),
});

const rawConversationResponseSchema = z.object({
  conversations: z
    .array(
      z.object({
        agent: z.string(),
        user_message: z.string(),
        assistant_response: z.string().nullable().optional(),
        tools_used: z.array(z.string()).default([]),
        duration_ms: z.number().nullable().optional(),
        thread_id: z.string(),
        timestamp: z.string(),
      })
    )
    .default([]),
});

const rawOutputsResponseSchema = z.object({
  outputs: z
    .array(
      z.object({
        path: z.string(),
        size_bytes: z.number().int().nonnegative().default(0),
        modified: z.number().default(0),
      })
    )
    .default([]),
});

const rawPatternsResponseSchema = z.object({
  timestamp: z.string(),
  period_hours: z.number().int().nonnegative().default(24),
  event_count: z.number().int().nonnegative().default(0),
  activity_count: z.number().int().nonnegative().default(0),
  patterns: z
    .array(
      z.object({
        type: z.string(),
        severity: z.string().default("low"),
        agent: z.string().nullable().optional(),
        count: z.number().nullable().optional(),
        sample_errors: z.array(z.string()).optional(),
        thumbs_up: z.number().nullable().optional(),
        thumbs_down: z.number().nullable().optional(),
        topics: z.record(z.string(), z.number()).optional(),
        dominant_type: z.string().nullable().optional(),
        actions: z.record(z.string(), z.number()).optional(),
      })
    )
    .default([]),
  recommendations: z.array(z.string()).default([]),
  autonomy_adjustments: z
    .array(
      z.object({
        agent: z.string(),
        category: z.string(),
        previous: z.number(),
        delta: z.number(),
        new: z.number(),
      })
    )
    .default([]),
  agent_behavioral_patterns: z
    .record(
      z.string(),
      z.object({
        dominant_topic: z.string().nullable().optional(),
        dominant_type: z.string().nullable().optional(),
        entity_count: z.number().nullable().optional(),
        actions: z.record(z.string(), z.number()).optional(),
      })
    )
    .default({}),
});

const rawLearningResponseSchema = z.object({
  timestamp: z.string(),
  metrics: z
    .object({
      cache: z
        .object({
          total_entries: z.number().nullable().optional(),
          hit_rate: z.number().nullable().optional(),
          tokens_saved: z.number().nullable().optional(),
          avg_similarity: z.number().nullable().optional(),
        })
        .nullable()
        .optional(),
      circuits: z
        .object({
          services: z.number().nullable().optional(),
          open: z.number().nullable().optional(),
          half_open: z.number().nullable().optional(),
          closed: z.number().nullable().optional(),
          total_failures: z.number().nullable().optional(),
        })
        .nullable()
        .optional(),
      preferences: z
        .object({
          model_task_pairs: z.number().nullable().optional(),
          total_samples: z.number().nullable().optional(),
          avg_composite_score: z.number().nullable().optional(),
          converged: z.number().nullable().optional(),
        })
        .nullable()
        .optional(),
      trust: z
        .object({
          agents_tracked: z.number().nullable().optional(),
          avg_trust_score: z.number().nullable().optional(),
          high_trust: z.number().nullable().optional(),
          low_trust: z.number().nullable().optional(),
        })
        .nullable()
        .optional(),
      diagnosis: z
        .object({
          recent_failures: z.number().nullable().optional(),
          patterns_detected: z.number().nullable().optional(),
          auto_remediations: z.number().nullable().optional(),
        })
        .nullable()
        .optional(),
      memory: z
        .object({
          collections: z.number().nullable().optional(),
          total_points: z.number().nullable().optional(),
        })
        .nullable()
        .optional(),
      tasks: z
        .object({
          total: z.number().nullable().optional(),
          completed: z.number().nullable().optional(),
          failed: z.number().nullable().optional(),
          success_rate: z.number().nullable().optional(),
        })
        .nullable()
        .optional(),
    })
    .passthrough(),
  summary: z.object({
    overall_health: z.number().nullable().optional(),
    data_points: z.number().nullable().optional(),
    positive_signals: z.array(z.string()).default([]),
    assessment: z.string().nullable().optional(),
  }),
});

const rawImprovementSchema = z.object({
  total_proposals: z.number().int().nonnegative().default(0),
  pending: z.number().int().nonnegative().default(0),
  validated: z.number().int().nonnegative().default(0),
  deployed: z.number().int().nonnegative().default(0),
  failed: z.number().int().nonnegative().default(0),
  benchmark_results: z.number().int().nonnegative().default(0),
  last_cycle: z
    .object({
      timestamp: z.string(),
      patterns_consumed: z.number().int().nonnegative().default(0),
      proposals_generated: z.number().int().nonnegative().default(0),
      benchmarks: z
        .object({
          passed: z.number().int().nonnegative().default(0),
          total: z.number().int().nonnegative().default(0),
          pass_rate: z.number().default(0),
        })
        .nullable()
        .optional(),
    })
    .nullable()
    .optional(),
});

const rawPreferencesResponseSchema = z.object({
  preferences: z
    .array(
      z.object({
        score: z.number(),
        content: z.string(),
        signal_type: z.string(),
        agent: z.string(),
        category: z.string().nullable().optional(),
        timestamp: z.string(),
      })
    )
    .default([]),
});

const qdrantCollectionStatsSchema = z.object({
  result: z.object({
    points_count: z.number().int().nonnegative().default(0),
    vectors_count: z.number().int().nonnegative().default(0),
    segments_count: z.number().int().nonnegative().default(0),
    status: z.string().default("red"),
  }),
});

const qdrantScrollSchema = z.object({
  result: z.object({
    points: z
      .array(
        z.object({
          id: z.union([z.string(), z.number()]),
          payload: z.record(z.string(), z.unknown()).default({}),
        })
      )
      .default([]),
    next_page_offset: z.union([z.string(), z.number(), z.null()]).optional(),
  }),
});

const neo4jResponseSchema = z.object({
  results: z
    .array(
      z.object({
        data: z.array(z.object({ row: z.array(z.unknown()) })).default([]),
      })
    )
    .default([]),
  errors: z.array(z.object({ message: z.string() })).default([]),
});

const prometheusInstantResponseSchema = z.object({
  status: z.string(),
  data: z.object({
    result: z.array(
      z.object({
        metric: z.record(z.string(), z.string()),
        value: z.tuple([z.number(), z.string()]),
      })
    ),
  }),
});

const prometheusRangeResponseSchema = z.object({
  status: z.string(),
  data: z.object({
    result: z.array(
      z.object({
        metric: z.record(z.string(), z.string()),
        values: z.array(z.tuple([z.number(), z.string()])),
      })
    ),
  }),
});

const rawMediaResponseSchema = z.object({
  plex_activity: z
    .object({
      stream_count: z.number().int().nonnegative().optional(),
      sessions: z
        .array(
          z.object({
            friendly_name: z.string().nullable().optional(),
            full_title: z.string().nullable().optional(),
            state: z.string().nullable().optional(),
            progress_percent: z.string().nullable().optional(),
            transcode_decision: z.string().nullable().optional(),
            media_type: z.string().nullable().optional(),
            year: z.string().nullable().optional(),
            thumb: z.string().nullable().optional(),
          })
        )
        .default([]),
    })
    .default({ sessions: [] }),
  sonarr_queue: z.array(z.record(z.string(), z.unknown())).default([]),
  radarr_queue: z.array(z.record(z.string(), z.unknown())).default([]),
  tv_upcoming: z.array(z.record(z.string(), z.unknown())).default([]),
  movie_upcoming: z.array(z.record(z.string(), z.unknown())).default([]),
  tv_library: z.record(z.string(), z.unknown()).default({}),
  movie_library: z.record(z.string(), z.unknown()).default({}),
  watch_history: z.array(z.record(z.string(), z.unknown())).default([]),
});

const rawStashResponseSchema = z.object({
  stats: z
    .object({
      scene_count: z.number().nullable().optional(),
      image_count: z.number().nullable().optional(),
      performer_count: z.number().nullable().optional(),
      studio_count: z.number().nullable().optional(),
      tag_count: z.number().nullable().optional(),
      scenes_size: z.number().nullable().optional(),
      scenes_duration: z.number().nullable().optional(),
    })
    .nullable(),
});

const rawComfyHistorySchema = z.object({
  items: z
    .array(
      z.object({
        promptId: z.string(),
        prompt: z.string(),
        outputImages: z
          .array(
            z.object({
              filename: z.string(),
              subfolder: z.string(),
              type: z.string(),
            })
          )
          .default([]),
        timestamp: z.number(),
        outputPrefix: z.string(),
      })
    )
    .default([]),
});

const rawComfyQueueSchema = z.object({
  queue_running: z.array(z.unknown()).default([]),
  queue_pending: z.array(z.unknown()).default([]),
});

const rawComfyStatsSchema = z.object({
  system: z
    .object({
      devices: z
        .array(
          z.object({
            name: z.string(),
            vram_total: z.number(),
            vram_free: z.number(),
          })
        )
        .default([]),
    })
    .nullable()
    .optional(),
});

function nowIso() {
  return new Date().toISOString();
}

async function fetchJsonSafe<T>(url: string, schema: z.ZodSchema<T>, fallback: T, init?: RequestInit) {
  try {
    const response = await fetch(url, {
      ...init,
      signal: init?.signal ?? AbortSignal.timeout(8000),
    });
    if (!response.ok) {
      return fallback;
    }
    return schema.parse(await response.json());
  } catch {
    return fallback;
  }
}

function inferProjectId(...values: Array<string | null | undefined>) {
  const combined = values
    .filter((value): value is string => Boolean(value))
    .join(" ")
    .toLowerCase();
  if (
    combined.includes("eoq") ||
    combined.includes("eobq") ||
    combined.includes("empire of broken queens")
  ) {
    return "eoq";
  }
  if (combined.includes("kindred")) {
    return "kindred";
  }
  if (combined.includes("media") || combined.includes("plex") || combined.includes("sonarr")) {
    return "media";
  }
  if (combined.includes("athanor")) {
    return "athanor";
  }
  return null;
}

function fileCategory(path: string) {
  const normalized = path.toLowerCase();
  if (normalized.includes("character")) {
    return "character";
  }
  if (normalized.includes("scene")) {
    return "scene";
  }
  if (normalized.includes("component") || normalized.endsWith(".tsx") || normalized.endsWith(".ts")) {
    return "component";
  }
  if (normalized.includes("test")) {
    return "test";
  }
  if (normalized.endsWith(".md")) {
    return "research";
  }
  return "output";
}

function hasFileOps(task: { prompt?: string | null; result?: string | null; error?: string | null; agentId?: string | null }) {
  const combined = [task.prompt, task.result, task.error, task.agentId]
    .filter((value): value is string => Boolean(value))
    .join(" ")
    .toLowerCase();
  return (
    task.agentId === "coding-agent" ||
    combined.includes("file") ||
    combined.includes("diff") ||
    combined.includes("write") ||
    combined.includes("renderer")
  );
}

async function neo4jQuery(statement: string) {
  const authHeader = getNeo4jAuthHeader();
  if (!authHeader) {
    return null;
  }

  return fetchJsonSafe(
    `${config.neo4j.url}/db/neo4j/tx/commit`,
    neo4jResponseSchema,
    null,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: authHeader,
      },
      body: JSON.stringify({ statements: [{ statement }] }),
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 60 },
    }
  );
}

async function queryPrometheus(query: string) {
  const url = `${config.prometheus.url}/api/v1/query?query=${encodeURIComponent(query)}`;
  const data = await fetchJsonSafe(url, prometheusInstantResponseSchema, null, {
    signal: AbortSignal.timeout(5000),
    next: { revalidate: 15 },
  });
  return data?.data.result ?? [];
}

async function queryPrometheusRange(query: string, start: number, end: number, step: number) {
  const params = new URLSearchParams({
    query,
    start: start.toString(),
    end: end.toString(),
    step: step.toString(),
  });
  const url = `${config.prometheus.url}/api/v1/query_range?${params}`;
  const data = await fetchJsonSafe(url, prometheusRangeResponseSchema, null, {
    signal: AbortSignal.timeout(5000),
    next: { revalidate: 15 },
  });
  return data?.data.result ?? [];
}

export async function getHistorySnapshot(): Promise<HistorySnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureHistorySnapshot();
  }

  const [projects, workforce, activityResponse, conversationResponse, outputsResponse] = await Promise.all([
    getProjectsSnapshot(),
    getWorkforceSnapshot(),
    fetchJsonSafe(joinUrl(config.agentServer.url, "/v1/activity?limit=60"), rawActivityResponseSchema, {
      activity: [],
    }),
    fetchJsonSafe(
      joinUrl(config.agentServer.url, "/v1/conversations?limit=40"),
      rawConversationResponseSchema,
      { conversations: [] }
    ),
    fetchJsonSafe(joinUrl(config.agentServer.url, "/v1/outputs"), rawOutputsResponseSchema, {
      outputs: [],
    }),
  ]);

  const activity = activityResponse.activity.map((item, index) => {
    const relatedTask = workforce.tasks.find((task) =>
      task.agentId === item.agent &&
      task.prompt.toLowerCase().includes(item.input_summary.toLowerCase().slice(0, 20))
    );
    const projectId = relatedTask?.projectId ?? inferProjectId(item.input_summary, item.output_summary);
    return {
      id: `activity-${index + 1}`,
      agentId: item.agent,
      projectId,
      actionType: item.action_type,
      inputSummary: item.input_summary,
      outputSummary: item.output_summary ?? null,
      toolsUsed: item.tools_used,
      durationMs: item.duration_ms ?? null,
      timestamp: item.timestamp,
      relatedTaskId: relatedTask?.id ?? null,
      relatedThreadId: null,
      reviewTaskId:
        relatedTask && ["pending_approval", "failed"].includes(relatedTask.status) ? relatedTask.id : null,
      status: relatedTask?.status ?? null,
      href: `/activity?selection=activity-${index + 1}`,
    };
  });

  const conversations = conversationResponse.conversations.map((item, index) => {
    const relatedTask = workforce.tasks.find(
      (task) =>
        task.agentId === item.agent &&
        task.prompt.toLowerCase().includes(item.user_message.toLowerCase().slice(0, 20))
    );
    return {
      id: `conversation-${index + 1}`,
      threadId: item.thread_id,
      agentId: item.agent,
      projectId:
        relatedTask?.projectId ?? inferProjectId(item.user_message, item.assistant_response ?? undefined),
      userMessage: item.user_message,
      assistantResponse: item.assistant_response ?? null,
      toolsUsed: item.tools_used,
      durationMs: item.duration_ms ?? null,
      timestamp: item.timestamp,
      relatedTaskId: relatedTask?.id ?? null,
      href: `/conversations?selection=${encodeURIComponent(item.thread_id)}`,
    };
  });

  const outputs = outputsResponse.outputs.map((item, index) => {
    const taskMatch = workforce.tasks.find(
      (task) =>
        (task.projectId && item.path.toLowerCase().includes(task.projectId)) ||
        (task.prompt && item.path.toLowerCase().includes(task.prompt.toLowerCase().slice(0, 16)))
    );
    return {
      id: `output-${index + 1}`,
      path: item.path,
      fileName: item.path.split("/").at(-1) ?? item.path,
      category: fileCategory(item.path),
      sizeBytes: item.size_bytes,
      modifiedAt: new Date(item.modified * 1000).toISOString(),
      projectId: taskMatch?.projectId ?? inferProjectId(item.path),
      relatedTaskId: taskMatch?.id ?? null,
      previewAvailable: !/\.(png|jpe?g|webp|gif|mp4)$/i.test(item.path),
      href: `/outputs?selection=output-${index + 1}`,
    };
  });

  return historySnapshotSchema.parse({
    generatedAt: nowIso(),
    summary: {
      activityCount: activity.length,
      conversationCount: conversations.length,
      outputCount: outputs.length,
      reviewCount: workforce.tasks.filter(
        (task) => ["pending_approval", "failed"].includes(task.status) || hasFileOps(task)
      ).length,
    },
    projects: projects.projects,
    agents: workforce.agents,
    tasks: workforce.tasks,
    activity,
    conversations,
    outputs,
  });
}

export async function getIntelligenceSnapshot(): Promise<IntelligenceSnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureIntelligenceSnapshot();
  }

  const [projects, workforce, rawPatterns, rawLearning, rawImprovement] = await Promise.all([
    getProjectsSnapshot(),
    getWorkforceSnapshot(),
    fetchJsonSafe(joinUrl(config.agentServer.url, "/v1/patterns"), rawPatternsResponseSchema, {
      timestamp: nowIso(),
      period_hours: 24,
      event_count: 0,
      activity_count: 0,
      patterns: [],
      recommendations: [],
      autonomy_adjustments: [],
      agent_behavioral_patterns: {},
    }),
    fetchJsonSafe(
      joinUrl(config.agentServer.url, "/v1/learning/metrics"),
      rawLearningResponseSchema,
      {
        timestamp: nowIso(),
        metrics: {},
        summary: {
          overall_health: 0,
          data_points: 0,
          positive_signals: [],
          assessment: "Unavailable",
        },
      }
    ),
    fetchJsonSafe(joinUrl(config.agentServer.url, "/v1/improvement/summary"), rawImprovementSchema, {
      total_proposals: 0,
      pending: 0,
      validated: 0,
      deployed: 0,
      failed: 0,
      benchmark_results: 0,
      last_cycle: null,
    }),
  ]);

  return intelligenceSnapshotSchema.parse({
    generatedAt: nowIso(),
    projects: projects.projects,
    agents: workforce.agents,
    report: {
      timestamp: rawPatterns.timestamp,
      periodHours: rawPatterns.period_hours,
      eventCount: rawPatterns.event_count,
      activityCount: rawPatterns.activity_count,
      patterns: rawPatterns.patterns.map((pattern) => ({
        type: pattern.type,
        severity:
          pattern.severity === "high" || pattern.severity === "medium" || pattern.severity === "low"
            ? pattern.severity
            : "low",
        agentId: pattern.agent ?? null,
        count: pattern.count ?? null,
        sampleErrors: pattern.sample_errors ?? [],
        thumbsUp: pattern.thumbs_up ?? null,
        thumbsDown: pattern.thumbs_down ?? null,
        topics: pattern.topics ?? {},
        dominantType: pattern.dominant_type ?? null,
        actions: pattern.actions ?? {},
      })),
      recommendations: rawPatterns.recommendations,
      autonomyAdjustments: rawPatterns.autonomy_adjustments.map((adjustment) => ({
        agentId: adjustment.agent,
        category: adjustment.category,
        previous: adjustment.previous,
        delta: adjustment.delta,
        next: adjustment.new,
      })),
      agentBehavior: Object.entries(rawPatterns.agent_behavioral_patterns).map(([agentId, entry]) => ({
        agentId,
        dominantTopic: entry.dominant_topic ?? null,
        dominantType: entry.dominant_type ?? null,
        entityCount: entry.entity_count ?? null,
        actions: entry.actions ?? {},
      })),
    },
    learning: {
      timestamp: rawLearning.timestamp,
      metrics: {
        cache: rawLearning.metrics.cache
          ? {
              totalEntries: rawLearning.metrics.cache.total_entries ?? null,
              hitRate: rawLearning.metrics.cache.hit_rate ?? null,
              tokensSaved: rawLearning.metrics.cache.tokens_saved ?? null,
              avgSimilarity: rawLearning.metrics.cache.avg_similarity ?? null,
            }
          : null,
        circuits: rawLearning.metrics.circuits
          ? {
              services: rawLearning.metrics.circuits.services ?? null,
              open: rawLearning.metrics.circuits.open ?? null,
              halfOpen: rawLearning.metrics.circuits.half_open ?? null,
              closed: rawLearning.metrics.circuits.closed ?? null,
              totalFailures: rawLearning.metrics.circuits.total_failures ?? null,
            }
          : null,
        preferences: rawLearning.metrics.preferences
          ? {
              modelTaskPairs: rawLearning.metrics.preferences.model_task_pairs ?? null,
              totalSamples: rawLearning.metrics.preferences.total_samples ?? null,
              avgCompositeScore: rawLearning.metrics.preferences.avg_composite_score ?? null,
              converged: rawLearning.metrics.preferences.converged ?? null,
            }
          : null,
        trust: rawLearning.metrics.trust
          ? {
              agentsTracked: rawLearning.metrics.trust.agents_tracked ?? null,
              avgTrustScore: rawLearning.metrics.trust.avg_trust_score ?? null,
              highTrust: rawLearning.metrics.trust.high_trust ?? null,
              lowTrust: rawLearning.metrics.trust.low_trust ?? null,
            }
          : null,
        diagnosis: rawLearning.metrics.diagnosis
          ? {
              recentFailures: rawLearning.metrics.diagnosis.recent_failures ?? null,
              patternsDetected: rawLearning.metrics.diagnosis.patterns_detected ?? null,
              autoRemediations: rawLearning.metrics.diagnosis.auto_remediations ?? null,
            }
          : null,
        memory: rawLearning.metrics.memory
          ? {
              collections: rawLearning.metrics.memory.collections ?? null,
              totalPoints: rawLearning.metrics.memory.total_points ?? null,
            }
          : null,
        tasks: rawLearning.metrics.tasks
          ? {
              total: rawLearning.metrics.tasks.total ?? null,
              completed: rawLearning.metrics.tasks.completed ?? null,
              failed: rawLearning.metrics.tasks.failed ?? null,
              successRate: rawLearning.metrics.tasks.success_rate ?? null,
            }
          : null,
      },
      summary: {
        overallHealth: rawLearning.summary.overall_health ?? null,
        dataPoints: rawLearning.summary.data_points ?? null,
        positiveSignals: rawLearning.summary.positive_signals ?? [],
        assessment: rawLearning.summary.assessment ?? null,
      },
    },
    improvement: {
      totalProposals: rawImprovement.total_proposals,
      pending: rawImprovement.pending,
      validated: rawImprovement.validated,
      deployed: rawImprovement.deployed,
      failed: rawImprovement.failed,
      benchmarkResults: rawImprovement.benchmark_results,
      lastCycle: rawImprovement.last_cycle
        ? {
            timestamp: rawImprovement.last_cycle.timestamp,
            patternsConsumed: rawImprovement.last_cycle.patterns_consumed,
            proposalsGenerated: rawImprovement.last_cycle.proposals_generated,
            benchmarks: rawImprovement.last_cycle.benchmarks
              ? {
                  passed: rawImprovement.last_cycle.benchmarks.passed,
                  total: rawImprovement.last_cycle.benchmarks.total,
                  passRate: rawImprovement.last_cycle.benchmarks.pass_rate,
                }
              : null,
          }
        : null,
    },
    reviewTasks: workforce.tasks.filter(
      (task) =>
        ["pending_approval", "failed"].includes(task.status) ||
        (hasFileOps(task) && task.status === "completed")
    ),
  });
}

async function getQdrantStats() {
  return fetchJsonSafe(
    `${config.qdrant.url}/collections/personal_data`,
    qdrantCollectionStatsSchema,
    null,
    {
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 60 },
    }
  );
}

async function getQdrantItems(limit: number) {
  const response = await fetchJsonSafe(
    `${config.qdrant.url}/collections/personal_data/points/scroll`,
    qdrantScrollSchema,
    { result: { points: [] } },
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        limit,
        with_payload: true,
        with_vector: false,
      }),
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 60 },
    }
  );
  return response.result.points;
}

export async function getMemorySnapshot(): Promise<MemorySnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureMemorySnapshot();
  }

  const [projects, qdrantStats, qdrantItems, rawPreferences, nodeCountRes, relCountRes, labelsRes, topTopicsRes] =
    await Promise.all([
      getProjectsSnapshot(),
      getQdrantStats(),
      getQdrantItems(120),
      fetchJsonSafe(
        joinUrl(config.agentServer.url, "/v1/preferences?query=operator&limit=8"),
        rawPreferencesResponseSchema,
        { preferences: [] }
      ),
      neo4jQuery("MATCH (n) RETURN count(n) as count"),
      neo4jQuery("MATCH ()-[r]->() RETURN count(r) as count"),
      neo4jQuery("CALL db.labels() YIELD label RETURN label ORDER BY label"),
      neo4jQuery(
        "MATCH (t:Topic)-[r]-() RETURN t.name as name, count(r) as connections ORDER BY connections DESC LIMIT 6"
      ),
    ]);

  const byCategory = new Map<string, number>();
  const recentItems = qdrantItems
    .map((point) => {
      const payload = point.payload;
      const indexedAt = typeof payload.indexed_at === "string" ? payload.indexed_at : null;
      const category = typeof payload.category === "string" ? payload.category : null;
      if (category) {
        byCategory.set(category, (byCategory.get(category) ?? 0) + 1);
      }
      return {
        id: point.id,
        title:
          (typeof payload.title === "string" && payload.title) ||
          (typeof payload.name === "string" && payload.name) ||
          "Untitled",
        url: typeof payload.url === "string" ? payload.url : null,
        source: typeof payload.source === "string" ? payload.source : null,
        category,
        subcategory: typeof payload.subcategory === "string" ? payload.subcategory : null,
        description: typeof payload.description === "string" ? payload.description : null,
        indexedAt,
      };
    })
    .sort((left, right) => (right.indexedAt ?? "").localeCompare(left.indexedAt ?? ""))
    .slice(0, 10);

  const graphNodes = Number(nodeCountRes?.results?.[0]?.data?.[0]?.row?.[0] ?? 0);
  const graphRelationships = Number(relCountRes?.results?.[0]?.data?.[0]?.row?.[0] ?? 0);

  return memorySnapshotSchema.parse({
    generatedAt: nowIso(),
    projects: projects.projects,
    summary: {
      qdrantOnline: Boolean(qdrantStats),
      neo4jOnline: Boolean(nodeCountRes && relCountRes),
      points: qdrantStats?.result.points_count ?? 0,
      vectors: qdrantStats?.result.vectors_count ?? 0,
      graphNodes,
      graphRelationships,
    },
    preferences: rawPreferences.preferences.map((preference) => ({
      score: preference.score,
      content: preference.content,
      signalType: preference.signal_type,
      agentId: preference.agent,
      category: preference.category ?? null,
      timestamp: preference.timestamp,
    })),
    recentItems,
    categories: Array.from(byCategory.entries())
      .sort((left, right) => right[1] - left[1])
      .slice(0, 8)
      .map(([name, count]) => ({ name, count })),
    topTopics: (topTopicsRes?.results?.[0]?.data ?? []).map((row) => ({
      name: String(row.row[0] ?? "topic"),
      connections: Number(row.row[1] ?? 0),
    })),
    graphLabels: (labelsRes?.results?.[0]?.data ?? []).map((row) => String(row.row[0] ?? "")),
  });
}

function parsePrometheusValue(
  results: Array<{ metric: Record<string, string>; value: [number, string] }>,
  ip: string
) {
  const result = results.find((entry) => (entry.metric.instance ?? "").includes(ip));
  return result ? Number.parseFloat(result.value[1]) : null;
}

function parsePrometheusHistory(
  results: Array<{ metric: Record<string, string>; values: [number, string][] }>,
  ip: string
) {
  const result = results.find((entry) => (entry.metric.instance ?? "").includes(ip));
  return result?.values.map((value) => Number.parseFloat(value[1])) ?? [];
}

export async function getMonitoringSnapshot(): Promise<MonitoringSnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureMonitoringSnapshot();
  }

  const now = Math.floor(Date.now() / 1000);
  const oneHourAgo = now - 3600;

  const [
    cpuUsage,
    memAvailable,
    memTotal,
    diskUsed,
    diskTotal,
    netRx,
    netTx,
    uptime,
    load1,
    cpuHistory,
    memHistory,
  ] = await Promise.all([
    queryPrometheus('100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'),
    queryPrometheus("node_memory_MemAvailable_bytes"),
    queryPrometheus("node_memory_MemTotal_bytes"),
    queryPrometheus(
      'node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_avail_bytes{mountpoint="/"}'
    ),
    queryPrometheus('node_filesystem_size_bytes{mountpoint="/"}'),
    queryPrometheus(
      'sum by (instance) (rate(node_network_receive_bytes_total{device!="lo"}[5m]))'
    ),
    queryPrometheus(
      'sum by (instance) (rate(node_network_transmit_bytes_total{device!="lo"}[5m]))'
    ),
    queryPrometheus("node_time_seconds - node_boot_time_seconds"),
    queryPrometheus("node_load1"),
    queryPrometheusRange(
      '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
      oneHourAgo,
      now,
      60
    ),
    queryPrometheusRange(
      "100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)",
      oneHourAgo,
      now,
      60
    ),
  ]);

  const nodes = config.nodes.map((node) => {
    const available = parsePrometheusValue(memAvailable, node.ip);
    const total = parsePrometheusValue(memTotal, node.ip);
    return {
      id: node.id,
      name: node.name,
      ip: node.ip,
      role: node.role,
      cpuUsage: parsePrometheusValue(cpuUsage, node.ip),
      memUsed: total !== null && available !== null ? total - available : null,
      memTotal: total,
      diskUsed: parsePrometheusValue(diskUsed, node.ip),
      diskTotal: parsePrometheusValue(diskTotal, node.ip),
      networkRxRate: parsePrometheusValue(netRx, node.ip),
      networkTxRate: parsePrometheusValue(netTx, node.ip),
      uptime: parsePrometheusValue(uptime, node.ip),
      load1: parsePrometheusValue(load1, node.ip),
      cpuHistory: parsePrometheusHistory(cpuHistory, node.ip),
      memHistory: parsePrometheusHistory(memHistory, node.ip),
    };
  });

  return monitoringSnapshotSchema.parse({
    generatedAt: nowIso(),
    summary: {
      reachableNodes: nodes.filter((node) => node.cpuUsage !== null).length,
      totalNodes: nodes.length,
      averageCpu: average(nodes.map((node) => node.cpuUsage).filter((value): value is number => value !== null)),
      totalMemUsed: nodes.reduce((sum, node) => sum + (node.memUsed ?? 0), 0),
      totalMemTotal: nodes.reduce((sum, node) => sum + (node.memTotal ?? 0), 0),
      networkRxRate: nodes.reduce((sum, node) => sum + (node.networkRxRate ?? 0), 0),
      networkTxRate: nodes.reduce((sum, node) => sum + (node.networkTxRate ?? 0), 0),
    },
    nodes,
    dashboards: config.grafanaDashboards,
  });
}

export async function getMediaSnapshot(): Promise<MediaSnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureMediaSnapshot();
  }

  const [media, stashGraphql] = await Promise.all([
    fetchJsonSafe(joinUrl(config.agentServer.url, "/v1/status/media"), rawMediaResponseSchema, {
      plex_activity: { sessions: [] },
      sonarr_queue: [],
      radarr_queue: [],
      tv_upcoming: [],
      movie_upcoming: [],
      tv_library: {},
      movie_library: {},
      watch_history: [],
    }),
    fetchJsonSafe(`${config.stash.url}/graphql`, z.unknown(), null, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: `{
          stats {
            scene_count
            image_count
            performer_count
            studio_count
            tag_count
            scenes_size
            scenes_duration
          }
        }`,
      }),
      signal: AbortSignal.timeout(5000),
    }),
  ]);

  const stash = rawStashResponseSchema.safeParse((stashGraphql as { data?: unknown })?.data).success
    ? rawStashResponseSchema.parse((stashGraphql as { data: unknown }).data)
    : { stats: null };

  const downloads = [
    ...media.sonarr_queue.map((item, index) => ({
      id: `sonarr-${index + 1}`,
      title: typeof item.title === "string" ? item.title : null,
      source: "Sonarr",
      progressPercent:
        typeof item.size === "number" && typeof item.sizeleft === "number" && item.size > 0
          ? ((item.size - item.sizeleft) / item.size) * 100
          : null,
      status: typeof item.status === "string" ? item.status : null,
      timeLeft: typeof item.timeleft === "string" ? item.timeleft : null,
    })),
    ...media.radarr_queue.map((item, index) => ({
      id: `radarr-${index + 1}`,
      title: typeof item.title === "string" ? item.title : null,
      source: "Radarr",
      progressPercent:
        typeof item.size === "number" && typeof item.sizeleft === "number" && item.size > 0
          ? ((item.size - item.sizeleft) / item.size) * 100
          : null,
      status: typeof item.status === "string" ? item.status : null,
      timeLeft: typeof item.timeleft === "string" ? item.timeleft : null,
    })),
  ];

  return mediaSnapshotSchema.parse({
    generatedAt: nowIso(),
    streamCount: media.plex_activity.stream_count ?? media.plex_activity.sessions.length,
    sessions: media.plex_activity.sessions.map((session) => ({
      friendlyName: session.friendly_name ?? null,
      title: session.full_title ?? null,
      state: session.state ?? null,
      progressPercent: session.progress_percent ? Number.parseFloat(session.progress_percent) : null,
      transcodeDecision: session.transcode_decision ?? null,
      mediaType: session.media_type ?? null,
      year: session.year ?? null,
      thumb: session.thumb ?? null,
    })),
    downloads,
    tvUpcoming: media.tv_upcoming.map((item, index) => ({
      id: `tv-${index + 1}`,
      title:
        (typeof item.title === "string" && item.title) ||
        (typeof item.seriesTitle === "string" && item.seriesTitle) ||
        "Untitled",
      seriesTitle: typeof item.seriesTitle === "string" ? item.seriesTitle : null,
      seasonNumber: typeof item.seasonNumber === "number" ? item.seasonNumber : null,
      episodeNumber: typeof item.episodeNumber === "number" ? item.episodeNumber : null,
      airDateUtc: typeof item.airDateUtc === "string" ? item.airDateUtc : null,
      hasFile: typeof item.hasFile === "boolean" ? item.hasFile : null,
    })),
    movieUpcoming: media.movie_upcoming.map((item, index) => ({
      id: `movie-${index + 1}`,
      title: (typeof item.title === "string" && item.title) || "Untitled",
      seriesTitle: null,
      seasonNumber: null,
      episodeNumber: null,
      airDateUtc: typeof item.airDateUtc === "string" ? item.airDateUtc : null,
      hasFile: typeof item.hasFile === "boolean" ? item.hasFile : null,
    })),
    watchHistory: media.watch_history.map((item, index) => ({
      id: `watch-${index + 1}`,
      friendlyName: typeof item.friendly_name === "string" ? item.friendly_name : null,
      title: typeof item.full_title === "string" ? item.full_title : null,
      date: typeof item.date === "string" ? item.date : null,
      duration: typeof item.duration === "string" ? item.duration : null,
      watchedStatus: typeof item.watched_status === "number" ? item.watched_status : null,
    })),
    tvLibrary: {
      total: typeof media.tv_library.total === "number" ? media.tv_library.total : null,
      monitored: typeof media.tv_library.monitored === "number" ? media.tv_library.monitored : null,
      episodes: typeof media.tv_library.episodes === "number" ? media.tv_library.episodes : null,
      sizeGb: typeof media.tv_library.size_gb === "number" ? media.tv_library.size_gb : null,
      hasFile: null,
    },
    movieLibrary: {
      total: typeof media.movie_library.total === "number" ? media.movie_library.total : null,
      monitored: typeof media.movie_library.monitored === "number" ? media.movie_library.monitored : null,
      episodes: null,
      sizeGb: typeof media.movie_library.size_gb === "number" ? media.movie_library.size_gb : null,
      hasFile: typeof media.movie_library.has_file === "number" ? media.movie_library.has_file : null,
    },
    stash: stash.stats
      ? {
          sceneCount: stash.stats.scene_count ?? null,
          imageCount: stash.stats.image_count ?? null,
          performerCount: stash.stats.performer_count ?? null,
          studioCount: stash.stats.studio_count ?? null,
          tagCount: stash.stats.tag_count ?? null,
          scenesSize: stash.stats.scenes_size ?? null,
          scenesDuration: stash.stats.scenes_duration ?? null,
        }
      : null,
    launchLinks: [
      { id: "plex", label: "Plex", url: joinUrl(config.plex.url, "/web") },
      { id: "sonarr", label: "Sonarr", url: config.sonarr.url },
      { id: "radarr", label: "Radarr", url: config.radarr.url },
      { id: "stash", label: "Stash", url: config.stash.url },
      { id: "prowlarr", label: "Prowlarr", url: config.prowlarr.url },
      { id: "sabnzbd", label: "SABnzbd", url: config.sabnzbd.url },
    ],
  });
}

export async function getGallerySnapshot(): Promise<GallerySnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureGallerySnapshot();
  }

  const [history, queue, stats] = await Promise.all([
    fetchJsonSafe(`${config.comfyui.url}/history`, z.record(z.string(), z.unknown()), {}, {
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 0 },
    }),
    fetchJsonSafe(`${config.comfyui.url}/queue`, rawComfyQueueSchema, {
      queue_running: [],
      queue_pending: [],
    }, {
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 0 },
    }),
    fetchJsonSafe(`${config.comfyui.url}/system_stats`, rawComfyStatsSchema, { system: null }, {
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 0 },
    }),
  ]);

  const items = rawComfyHistorySchema.parse({
    items: Object.entries(history).flatMap(([promptId, entry]) => {
      const value = entry as {
        prompt?: [number, string, Record<string, { class_type: string; inputs: Record<string, unknown> }>];
        outputs?: Record<string, { images?: { filename: string; subfolder: string; type: string }[] }>;
      };
      if (!value.outputs) {
        return [];
      }
      const outputImages = Object.values(value.outputs).flatMap((output) => output.images ?? []);
      if (outputImages.length === 0) {
        return [];
      }

      let prompt = "";
      let outputPrefix = "";
      const workflow = value.prompt?.[2] ?? {};
      for (const node of Object.values(workflow)) {
        if (node.class_type === "CLIPTextEncode" && typeof node.inputs?.text === "string") {
          prompt = node.inputs.text;
        }
        if (node.class_type === "SaveImage" && typeof node.inputs?.filename_prefix === "string") {
          outputPrefix = node.inputs.filename_prefix;
        }
      }

      return [{ promptId, prompt, outputImages, timestamp: value.prompt?.[0] ?? 0, outputPrefix }];
    }),
  }).items;

  const device = stats.system?.devices?.[0] ?? null;

  return gallerySnapshotSchema.parse({
    generatedAt: nowIso(),
    queueRunning: queue.queue_running.length,
    queuePending: queue.queue_pending.length,
    deviceName: device?.name ?? null,
    vramUsedGiB: device ? (device.vram_total - device.vram_free) / 1024 ** 3 : null,
    vramTotalGiB: device ? device.vram_total / 1024 ** 3 : null,
    items: items
      .sort((left, right) => right.timestamp - left.timestamp)
      .slice(0, 60)
      .map((item) => ({
        id: item.promptId,
        prompt: item.prompt,
        outputPrefix: item.outputPrefix,
        timestamp: item.timestamp,
        outputImages: item.outputImages,
      })),
  });
}

export async function getHomeSnapshot(): Promise<HomeSnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureHomeSnapshot();
  }

  let online = false;
  try {
    const response = await fetch(joinUrl(config.homeAssistant.url, "/api/"), {
      signal: AbortSignal.timeout(3000),
      next: { revalidate: 60 },
    });
    online = response.status !== 404;
  } catch {
    online = false;
  }

  return homeSnapshotSchema.parse({
    generatedAt: nowIso(),
    online,
    configured: false,
    title: "Home Assistant",
    summary: online
      ? "Home Assistant is reachable. Finish onboarding and credential wiring to unlock focused panels."
      : "Home Assistant is not reachable from the current dashboard probe.",
    setupSteps: [
      {
        id: "ha-runtime",
        label: "Home Assistant runtime reachable",
        status: online ? "complete" : "pending",
        note: online ? "Dashboard probe can reach the Home Assistant API root." : "Probe failed or timed out.",
      },
      {
        id: "ha-onboarding",
        label: "Complete Home Assistant onboarding",
        status: online ? "pending" : "blocked",
        note: "Requires an authenticated browser session in Home Assistant.",
      },
      {
        id: "home-agent",
        label: "Enable home-agent operational lane",
        status: "blocked",
        note: "Wait until onboarding and credential wiring are complete.",
      },
      {
        id: "ha-panels",
        label: "Expose focused home-control panels in Athanor",
        status: "pending",
        note: "Panel drawers come after the core integration is verified live.",
      },
    ],
    panels: [
      {
        id: "lights",
        label: "Lights",
        description: "Room-level lighting scenes, brightness, and presence-aware overrides.",
        href: "/home?panel=lights",
      },
      {
        id: "climate",
        label: "Climate",
        description: "HVAC, temperature, and comfort-state monitoring.",
        href: "/home?panel=climate",
      },
      {
        id: "presence",
        label: "Presence",
        description: "Who is home, device presence, and routine triggers.",
        href: "/home?panel=presence",
      },
    ],
  });
}
