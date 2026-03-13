"use client";

import type { CSSProperties } from "react";

import { cn } from "@/lib/utils";

type ThemeSample = {
  id: string;
  name: string;
  family: string;
  description: string;
  fit: string;
  tags: string[];
  cluster: string;
  clusterLabel: string;
  hero: string;
  heroCopy: string;
  accent: string;
  ok: string;
  warn: string;
  danger: string;
  chart: [string, string, string];
  vars: {
    bg: string;
    rail: string;
    rail2: string;
    panel: string;
    panel2: string;
    hero: string;
    well: string;
    pill: string;
    pillActive: string;
    line: string;
    fg: string;
    muted: string;
    halo: string;
  };
};

const THEMES: ThemeSample[] = [
  {
    id: "pure-monochrome-oled",
    name: "Pure Monochrome OLED",
    family: "Contrast-first black UI",
    description:
      "Near-black background, white and gray structure, and one bright blue control accent. The most severe and operator-first option in the set.",
    fit: "Best if you want Athanor to feel pure, sharp, minimal, and uncompromising.",
    tags: ["Strong fit", "Minimal", "Black + white + bright accent"],
    cluster: "24/29",
    clusterLabel: "4 items need intervention",
    hero: "Control Core",
    heroCopy:
      "A hard-black interface with strict contrast and one clear active-state signal.",
    accent: "#4fb3ff",
    ok: "#3add98",
    warn: "#ffd24a",
    danger: "#ff6077",
    chart: ["#4fb3ff", "#d8dde6", "#6a7383"],
    vars: {
      bg: "#000000",
      rail: "#07080a",
      rail2: "#0d1014",
      panel: "#0a0d11",
      panel2: "#10151b",
      hero: "#0c1119",
      well: "#0e1217",
      pill: "#10141a",
      pillActive: "#121925",
      line: "rgba(255,255,255,.12)",
      fg: "#f6f8fb",
      muted: "#a6afbd",
      halo: "rgba(79,179,255,.17)",
    },
  },
  {
    id: "github-dark-dimmed",
    name: "GitHub Dark Dimmed",
    family: "Soft slate dark",
    description:
      "A calm dark mode with softened contrast, layered slate surfaces, and carefully limited blue accents. Mature and long-session friendly.",
    fit: "Best if you want serious product polish without a high-contrast command-bunker feel.",
    tags: ["Mature", "Low fatigue", "Productized"],
    cluster: "23/29",
    clusterLabel: "steady operating posture",
    hero: "Operations Deck",
    heroCopy:
      "Dimmed dark surfaces for long sessions, with bright accents reserved for actual state changes.",
    accent: "#6cb6ff",
    ok: "#57d364",
    warn: "#d29922",
    danger: "#f47067",
    chart: ["#6cb6ff", "#57d364", "#d29922"],
    vars: {
      bg: "#22272e",
      rail: "#1c2128",
      rail2: "#2d333b",
      panel: "#2a313c",
      panel2: "#303845",
      hero: "#27303a",
      well: "#262d36",
      pill: "#2d333b",
      pillActive: "#323b46",
      line: "rgba(205,217,229,.12)",
      fg: "#cdd9e5",
      muted: "#909dab",
      halo: "rgba(108,182,255,.14)",
    },
  },
  {
    id: "github-dark-high-contrast",
    name: "GitHub Dark High Contrast",
    family: "High-clarity operator dark",
    description:
      "A crisper, sharper variation of the product dark pattern with more decisive edges and clearer boundaries everywhere.",
    fit: "Best if speed of scanning matters more than atmosphere and you still want a polished mainstream reference.",
    tags: ["Operator clarity", "High contrast", "Sharp edges"],
    cluster: "ALERT",
    clusterLabel: "approval queue above threshold",
    hero: "Signal Board",
    heroCopy:
      "More decisive separation between shell, panels, actions, and alerts for fast operator scanning.",
    accent: "#71b7ff",
    ok: "#56d364",
    warn: "#e3b341",
    danger: "#ff7b72",
    chart: ["#71b7ff", "#e3b341", "#7ee787"],
    vars: {
      bg: "#0d1117",
      rail: "#010409",
      rail2: "#161b22",
      panel: "#161b22",
      panel2: "#1f2630",
      hero: "#111722",
      well: "#131a21",
      pill: "#1a212b",
      pillActive: "#1d2735",
      line: "rgba(240,246,252,.15)",
      fg: "#f0f6fc",
      muted: "#8b949e",
      halo: "rgba(113,183,255,.18)",
    },
  },
  {
    id: "carbon-ops",
    name: "Carbon Ops",
    family: "Industrial enterprise dark",
    description:
      "Dense charcoal surfaces, assertive separators, and disciplined IBM-style blue. More institutional and operational than expressive.",
    fit: "Best if you want Athanor to feel like a serious industrial platform instead of a boutique product.",
    tags: ["Industrial", "Dense", "Enterprise-grade"],
    cluster: "11",
    clusterLabel: "systems under observation",
    hero: "Operations Grid",
    heroCopy:
      "Built around dense instrumentation, firm hierarchy, and reliable enterprise-grade clarity.",
    accent: "#78a9ff",
    ok: "#42be65",
    warn: "#f1c21b",
    danger: "#fa4d56",
    chart: ["#78a9ff", "#42be65", "#be95ff"],
    vars: {
      bg: "#161616",
      rail: "#1a1a1a",
      rail2: "#262626",
      panel: "#262626",
      panel2: "#303030",
      hero: "#212121",
      well: "#1f1f1f",
      pill: "#2a2a2a",
      pillActive: "#323232",
      line: "rgba(244,244,244,.12)",
      fg: "#f4f4f4",
      muted: "#a8a8a8",
      halo: "rgba(120,169,255,.15)",
    },
  },
  {
    id: "gitlab-dark-restraint",
    name: "GitLab Dark Restraint",
    family: "Reduced-color enterprise dark",
    description:
      "Deep neutral surfaces with restrained color usage and a slightly plum-tinted shell. Less monochrome, but still disciplined.",
    fit: "Best if you want a dark enterprise UI that feels more designed than Carbon but less stylized than Nord or Catppuccin.",
    tags: ["Restrained color", "Enterprise", "Balanced"],
    cluster: "7",
    clusterLabel: "limited signal palette",
    hero: "Decision Rail",
    heroCopy:
      "Uses color sparingly and keeps structure and status readable without flooding the shell with accents.",
    accent: "#8cc4ff",
    ok: "#6fd6a6",
    warn: "#f7b955",
    danger: "#ff7b8f",
    chart: ["#8cc4ff", "#b4a3ff", "#f7b955"],
    vars: {
      bg: "#171321",
      rail: "#15111d",
      rail2: "#211a2d",
      panel: "#1f1a2a",
      panel2: "#262031",
      hero: "#201b2d",
      well: "#1b1726",
      pill: "#241e30",
      pillActive: "#2b2337",
      line: "rgba(255,255,255,.1)",
      fg: "#f5f3ff",
      muted: "#aba4ba",
      halo: "rgba(140,196,255,.14)",
    },
  },
  {
    id: "nord-arctic",
    name: "Nord Arctic",
    family: "Muted arctic dark",
    description:
      "A cool blue-gray control room with calm contrast and soft frost accents. Elegant, minimal, and easy on the eyes.",
    fit: "Best if you want something technical and beautiful, but less severe than pure monochrome.",
    tags: ["Cool", "Elegant", "Calm"],
    cluster: "stable",
    clusterLabel: "signal load within range",
    hero: "Frost Array",
    heroCopy:
      "Muted blue-gray neutrals with calm contrast and a distinctly cooler, clearer atmosphere.",
    accent: "#88c0d0",
    ok: "#a3be8c",
    warn: "#ebcb8b",
    danger: "#bf616a",
    chart: ["#88c0d0", "#81a1c1", "#b48ead"],
    vars: {
      bg: "#2e3440",
      rail: "#2b303b",
      rail2: "#3b4252",
      panel: "#3b4252",
      panel2: "#434c5e",
      hero: "#364050",
      well: "#323947",
      pill: "#404858",
      pillActive: "#475163",
      line: "rgba(236,239,244,.12)",
      fg: "#eceff4",
      muted: "#c0c8d6",
      halo: "rgba(136,192,208,.16)",
    },
  },
  {
    id: "catppuccin-mocha",
    name: "Catppuccin Mocha",
    family: "Soft expressive dark",
    description:
      "A richer, more expressive dark theme with softened edges and pastel accent families. Distinctly more emotional than the operator-heavy options.",
    fit: "Best if you want Athanor to feel more premium and alive without becoming neon or cyberpunk.",
    tags: ["Expressive", "Pastel dark", "Softened"],
    cluster: "12",
    clusterLabel: "active domains visible",
    hero: "Signal Lounge",
    heroCopy:
      "Warm-neutral dark materials with carefully coordinated pastel accents and a gentler overall feel.",
    accent: "#89b4fa",
    ok: "#a6e3a1",
    warn: "#f9e2af",
    danger: "#f38ba8",
    chart: ["#89b4fa", "#cba6f7", "#fab387"],
    vars: {
      bg: "#11111b",
      rail: "#181825",
      rail2: "#1e1e2e",
      panel: "#1e1e2e",
      panel2: "#252538",
      hero: "#202234",
      well: "#181928",
      pill: "#24273a",
      pillActive: "#2c3147",
      line: "rgba(205,214,244,.12)",
      fg: "#cdd6f4",
      muted: "#a6adc8",
      halo: "rgba(137,180,250,.16)",
    },
  },
  {
    id: "material-3-expressive-dark",
    name: "Material 3 Expressive Dark",
    family: "Role-rich semantic dark",
    description:
      "A more dynamic, multi-role dark system with richer secondary and tertiary accents and tonal surfaces that feel more app-system than terminal.",
    fit: "Best if you want more expressive semantic depth and route/domain flexibility, and less strict monochrome discipline.",
    tags: ["Role-rich", "Semantic", "Dynamic"],
    cluster: "adaptive",
    clusterLabel: "surface roles shifting by context",
    hero: "Adaptive Console",
    heroCopy:
      "A semantic color system built for richer surface roles, more expressive accents, and stronger route-by-route differentiation.",
    accent: "#a8c7fa",
    ok: "#7fd7c4",
    warn: "#f5c86b",
    danger: "#ffb4ab",
    chart: ["#a8c7fa", "#d0bcff", "#7fd7c4"],
    vars: {
      bg: "#10131a",
      rail: "#12161d",
      rail2: "#1a1f2a",
      panel: "#1b202b",
      panel2: "#242938",
      hero: "#1f2432",
      well: "#171c27",
      pill: "#242a35",
      pillActive: "#2d3442",
      line: "rgba(229,225,245,.12)",
      fg: "#e5e1f5",
      muted: "#b3b0c6",
      halo: "rgba(168,199,250,.15)",
    },
  },
];

const STREAM_ITEMS = [
  {
    title: "Backup drift detected",
    copy: "Vault qdrant backup is outside policy window.",
    tone: "danger" as const,
  },
  {
    title: "Sovereign route selected",
    copy: "Private content stayed local-only.",
    tone: "accent" as const,
  },
  {
    title: "Approval waiting",
    copy: "One task needs operator confirmation.",
    tone: "warn" as const,
  },
];

const WORKPLAN_ITEMS = [
  {
    title: "Refill coding queue",
    copy: "1 pending approval · 4 blocked",
    tone: "warn" as const,
  },
  {
    title: "Audit provider posture",
    copy: "Reserve below target",
    tone: "accent" as const,
  },
  {
    title: "Run consolidation",
    copy: "06:55 local window",
    tone: "ok" as const,
  },
];

type ToneKey = "accent" | "ok" | "warn" | "danger";

function toneColor(theme: ThemeSample, tone: ToneKey) {
  if (tone === "ok") return theme.ok;
  if (tone === "warn") return theme.warn;
  if (tone === "danger") return theme.danger;
  return theme.accent;
}

type ThemePreviewProps = {
  theme: ThemeSample;
};

function ThemePreview({ theme }: ThemePreviewProps) {
  const previewStyle = {
    borderColor: theme.vars.line,
    background: theme.vars.bg,
    color: theme.vars.fg,
    ["--sampler-bg" as string]: theme.vars.bg,
    ["--sampler-rail" as string]: theme.vars.rail,
    ["--sampler-rail-2" as string]: theme.vars.rail2,
    ["--sampler-panel" as string]: theme.vars.panel,
    ["--sampler-panel-2" as string]: theme.vars.panel2,
    ["--sampler-hero" as string]: theme.vars.hero,
    ["--sampler-well" as string]: theme.vars.well,
    ["--sampler-pill" as string]: theme.vars.pill,
    ["--sampler-pill-active" as string]: theme.vars.pillActive,
    ["--sampler-line" as string]: theme.vars.line,
    ["--sampler-fg" as string]: theme.vars.fg,
    ["--sampler-muted" as string]: theme.vars.muted,
    ["--sampler-accent" as string]: theme.accent,
    ["--sampler-halo" as string]: theme.vars.halo,
  } satisfies CSSProperties;

  return (
    <div className="overflow-hidden rounded-[1.35rem] border" style={previewStyle}>
      <div className="grid min-h-[33rem] grid-cols-[7rem_1fr]">
        <aside
          className="grid content-start gap-2 border-r px-3 py-3"
          style={{
            borderColor: "var(--sampler-line)",
            background:
              "linear-gradient(180deg, var(--sampler-rail-2), var(--sampler-rail))",
          }}
        >
          <div className="mb-1 grid gap-1">
            <span className="text-[9px] uppercase tracking-[0.24em]" style={{ color: "var(--sampler-muted)" }}>
              Athanor
            </span>
            <strong className="text-sm tracking-[-0.04em]">Command</strong>
            <div
              className="h-px"
              style={{
                background:
                  "linear-gradient(90deg, var(--sampler-accent), transparent)",
              }}
            />
          </div>
          {["Dashboard", "Agents", "Tasks", "Planner", "Alerts"].map((item, index) => (
            <div
              key={item}
              className={cn("rounded-xl border px-3 py-2 text-[10px]", index === 0 && "font-medium")}
              style={{
                borderColor:
                  index === 0
                    ? "color-mix(in srgb, var(--sampler-accent) 34%, transparent)"
                    : "transparent",
                background:
                  index === 0
                    ? "linear-gradient(90deg, color-mix(in srgb, var(--sampler-accent) 18%, transparent), transparent), var(--sampler-pill-active)"
                    : "var(--sampler-pill)",
                color: index === 0 ? "var(--sampler-fg)" : "var(--sampler-muted)",
              }}
            >
              {item}
            </div>
          ))}
          <div
            className="mt-auto rounded-2xl border p-3"
            style={{
              borderColor: "var(--sampler-line)",
              background: "var(--sampler-well)",
            }}
          >
            <div className="text-[9px] uppercase tracking-[0.22em]" style={{ color: "var(--sampler-muted)" }}>
              Cluster
            </div>
            <div className="text-2xl font-semibold tracking-[-0.06em]">{theme.cluster}</div>
            <div className="text-[10px]" style={{ color: "var(--sampler-muted)" }}>
              {theme.clusterLabel}
            </div>
          </div>
        </aside>

        <div
          className="grid grid-rows-[auto_1fr]"
          style={{
            background:
              "radial-gradient(circle at top left, var(--sampler-halo), transparent 26%), linear-gradient(180deg, var(--sampler-panel-2), var(--sampler-panel))",
          }}
        >
          <div
            className="flex items-center justify-between gap-4 border-b px-4 py-3"
            style={{
              borderColor: "var(--sampler-line)",
              background:
                "color-mix(in srgb, var(--sampler-panel-2) 86%, black)",
            }}
          >
            <div className="flex items-center gap-2 text-xs" style={{ color: "var(--sampler-muted)" }}>
              <span
                className="h-2 w-2 rounded-full"
                style={{
                  background: "var(--sampler-accent)",
                  boxShadow:
                    "0 0 18px color-mix(in srgb, var(--sampler-accent) 40%, transparent)",
                }}
              />
              Command Center
            </div>
            <div className="flex items-center gap-2">
              {[
                ["active", theme.accent],
                ["warn", theme.warn],
                ["risk", theme.danger],
              ].map(([label, color]) => (
                <span
                  key={label}
                  className="inline-flex items-center gap-2 rounded-full border px-3 py-2 text-[10px] uppercase tracking-[0.08em]"
                  style={{
                    borderColor: "var(--sampler-line)",
                    background: "var(--sampler-pill)",
                    color: "var(--sampler-muted)",
                  }}
                >
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
                  {label}
                </span>
              ))}
            </div>
          </div>

          <div className="grid gap-4 p-4">
            <div className="grid gap-3 lg:grid-cols-[1.15fr_0.85fr]">
              <div
                className="rounded-3xl border p-4"
                style={{
                  borderColor:
                    "color-mix(in srgb, var(--sampler-accent) 20%, var(--sampler-line))",
                  background: "var(--sampler-hero)",
                }}
              >
                <div className="text-[9px] uppercase tracking-[0.22em]" style={{ color: "var(--sampler-muted)" }}>
                  {theme.family}
                </div>
                <h3 className="mt-2 text-3xl font-semibold tracking-[-0.06em]">{theme.hero}</h3>
                <p className="mt-2 text-sm" style={{ color: "var(--sampler-muted)" }}>
                  {theme.heroCopy}
                </p>
              </div>
              <div className="grid content-start gap-2">
                <div className="flex flex-wrap gap-2">
                  <button
                    className="rounded-xl border px-3 py-2 text-[10px] uppercase tracking-[0.06em]"
                    style={{
                      borderColor: "transparent",
                      background: "var(--sampler-pill)",
                    }}
                  >
                    Open incidents
                  </button>
                  <button
                    className="rounded-xl border px-3 py-2 text-[10px] uppercase tracking-[0.06em]"
                    style={{
                      borderColor:
                        "color-mix(in srgb, var(--sampler-accent) 42%, transparent)",
                      background:
                        "color-mix(in srgb, var(--sampler-accent) 22%, var(--sampler-panel-2))",
                    }}
                  >
                    Resume agents
                  </button>
                </div>
                <button
                  className="w-fit rounded-xl border px-3 py-2 text-[10px] uppercase tracking-[0.06em]"
                  style={{
                    borderColor: "transparent",
                    background: "var(--sampler-pill)",
                  }}
                >
                  Open planner
                </button>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-4">
              {[
                ["Approvals", "1", "pending", theme.danger],
                ["Agents", "8", "2 active", theme.accent],
                ["Latency", "32ms", "nominal", theme.ok],
                ["Queue", "14", "4 running", theme.warn],
              ].map(([label, value, helper, signal]) => (
                <div
                  key={label}
                  className="rounded-3xl border p-4"
                  style={{
                    borderColor: "var(--sampler-line)",
                    background: "var(--sampler-well)",
                  }}
                >
                  <div className="flex items-center justify-between gap-2 text-[9px] uppercase tracking-[0.22em]">
                    <span style={{ color: "var(--sampler-muted)" }}>{label}</span>
                    <span className="h-1.5 w-1.5 rounded-full" style={{ background: signal }} />
                  </div>
                  <div className="mt-2 text-3xl font-semibold tracking-[-0.06em]">{value}</div>
                  <div className="text-xs" style={{ color: "var(--sampler-muted)" }}>
                    {helper}
                  </div>
                </div>
              ))}
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
              <div
                className="rounded-3xl border p-4"
                style={{
                  borderColor: "var(--sampler-line)",
                  background: "var(--sampler-panel)",
                }}
              >
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h4 className="text-2xl font-semibold tracking-[-0.05em]">Unified stream</h4>
                  <span
                    className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.08em]"
                    style={{
                      borderColor: "var(--sampler-line)",
                      background:
                        "color-mix(in srgb, var(--sampler-panel-2) 72%, black)",
                    }}
                  >
                    <span className="h-1.5 w-1.5 rounded-full" style={{ background: "var(--sampler-accent)" }} />
                    live
                  </span>
                </div>
                {STREAM_ITEMS.map((item, index) => (
                  <div
                    key={item.title}
                    className={cn("grid gap-1 py-3", index !== 0 && "border-t")}
                    style={{
                      borderColor: "color-mix(in srgb, var(--sampler-line) 78%, transparent)",
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ background: toneColor(theme, item.tone) }}
                      />
                      <strong className="text-xs font-semibold">{item.title}</strong>
                    </div>
                    <p className="text-xs" style={{ color: "var(--sampler-muted)" }}>
                      {item.copy}
                    </p>
                  </div>
                ))}
              </div>
              <div
                className="rounded-3xl border p-4"
                style={{
                  borderColor: "var(--sampler-line)",
                  background: "var(--sampler-panel)",
                }}
              >
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h4 className="text-2xl font-semibold tracking-[-0.05em]">Work Plan</h4>
                  <span
                    className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.08em]"
                    style={{
                      borderColor: "var(--sampler-line)",
                      background:
                        "color-mix(in srgb, var(--sampler-panel-2) 72%, black)",
                    }}
                  >
                    <span className="h-1.5 w-1.5 rounded-full" style={{ background: theme.ok }} />
                    steer
                  </span>
                </div>
                {WORKPLAN_ITEMS.map((item, index) => (
                  <div
                    key={item.title}
                    className={cn("grid gap-1 py-3", index !== 0 && "border-t")}
                    style={{
                      borderColor: "color-mix(in srgb, var(--sampler-line) 78%, transparent)",
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ background: toneColor(theme, item.tone) }}
                      />
                      <strong className="text-xs font-semibold">{item.title}</strong>
                    </div>
                    <p className="text-xs" style={{ color: "var(--sampler-muted)" }}>
                      {item.copy}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div
              className="rounded-3xl border p-4"
              style={{
                borderColor: "var(--sampler-line)",
                background:
                  "linear-gradient(180deg, color-mix(in srgb, var(--sampler-panel-2) 84%, black), var(--sampler-panel))",
              }}
            >
              <div className="mb-3 flex items-center justify-between gap-3">
                <h4 className="text-lg font-semibold tracking-[-0.04em]">Telemetry grammar</h4>
                <span className="text-[10px] uppercase tracking-[0.08em]" style={{ color: "var(--sampler-muted)" }}>
                  category colors only
                </span>
              </div>
              <div className="grid gap-3 md:grid-cols-[1.1fr_0.9fr]">
                <div className="grid gap-2">
                  {theme.chart.map((color, index) => (
                    <div key={color} className="grid gap-1">
                      <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.08em]">
                        <span style={{ color: "var(--sampler-muted)" }}>Lane {index + 1}</span>
                        <span style={{ color }}>{["62%", "48%", "31%"][index]}</span>
                      </div>
                      <div className="h-2 rounded-full" style={{ background: "color-mix(in srgb, var(--sampler-line) 45%, black)" }}>
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: ["62%", "48%", "31%"][index],
                            background: color,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="grid gap-2 sm:grid-cols-3 md:grid-cols-1">
                  {[
                    ["ok", theme.ok, "Healthy"],
                    ["warn", theme.warn, "Needs review"],
                    ["risk", theme.danger, "Intervention"],
                  ].map(([label, color, text]) => (
                    <div
                      key={label}
                      className="rounded-2xl border px-3 py-3"
                      style={{
                        borderColor: "var(--sampler-line)",
                        background: "var(--sampler-well)",
                      }}
                    >
                      <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.08em]">
                        <span className="h-2 w-2 rounded-full" style={{ background: color }} />
                        <span style={{ color: "var(--sampler-muted)" }}>{label}</span>
                      </div>
                      <div className="mt-1 text-sm font-medium">{text}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ThemeSampler() {
  return (
    <section id="theme-sampler" className="space-y-6">
      <div className="space-y-3">
        <div className="text-xs uppercase tracking-[0.26em] text-muted-foreground">
          Theme Sampler v2
        </div>
        <div className="space-y-2">
          <h2 className="font-heading text-3xl tracking-[-0.05em] text-foreground">
            Actually different dark-system families
          </h2>
          <p className="max-w-4xl text-sm leading-7 text-muted-foreground">
            Same miniature Command Center, but this time the options are built as distinct
            reference families inspired by respected dark systems. The point is to compare
            genuinely different visual identities, not six neighbors from one palette family.
          </p>
        </div>
      </div>

      <div className="grid gap-5 2xl:grid-cols-2">
        {THEMES.map((theme) => (
          <article key={theme.id} className="overflow-hidden rounded-[1.75rem] border surface-panel">
            <div className="grid gap-3 border-b border-[color:color-mix(in_oklab,var(--line-soft)_74%,transparent)] px-6 py-5">
              <div className="space-y-2">
                <div className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                  {theme.family}
                </div>
                <h3 className="text-xl font-semibold tracking-[-0.04em]">{theme.name}</h3>
                <p className="text-sm leading-6 text-muted-foreground">{theme.description}</p>
                <p className="text-sm leading-6 text-foreground/90">{theme.fit}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {theme.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.08em] text-muted-foreground"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            <div className="p-5">
              <ThemePreview theme={theme} />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
