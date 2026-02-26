export type LensId = "default" | "system" | "media" | "creative" | "eoq";

export type SectionId = "pulse" | "crew" | "gpus" | "workloads" | "stream" | "watches" | "links" | "digest" | "smartstack" | "workplan";

export interface LensConfig {
  id: LensId;
  label: string;
  icon: string;
  accent: string;
  accentHue: number;
  agents: string[];
  sections: SectionId[];
  streamFilter: string[];
  navHighlight: string[];
}

export const LENS_CONFIG: Record<LensId, LensConfig> = {
  default: {
    id: "default",
    label: "Overview",
    icon: "A",
    accent: "oklch(0.75 0.08 65)",
    accentHue: 65,
    agents: [],
    sections: ["pulse", "crew", "smartstack", "workplan", "gpus", "workloads", "stream", "watches", "links", "digest"],
    streamFilter: [],
    navHighlight: [],
  },
  system: {
    id: "system",
    label: "System",
    icon: "S",
    accent: "oklch(0.65 0.12 230)",
    accentHue: 230,
    agents: ["general-assistant", "coding-agent"],
    sections: ["pulse", "smartstack", "workplan", "gpus", "workloads", "crew", "stream", "links", "digest"],
    streamFilter: ["task", "system"],
    navHighlight: ["/gpu", "/services", "/monitoring", "/tasks"],
  },
  media: {
    id: "media",
    label: "Media",
    icon: "M",
    accent: "oklch(0.65 0.12 160)",
    accentHue: 160,
    agents: ["media-agent"],
    sections: ["pulse", "watches", "smartstack", "workplan", "crew", "stream", "workloads", "gpus", "links", "digest"],
    streamFilter: ["media", "task"],
    navHighlight: ["/media", "/gallery"],
  },
  creative: {
    id: "creative",
    label: "Creative",
    icon: "C",
    accent: "oklch(0.7 0.1 330)",
    accentHue: 330,
    agents: ["creative-agent"],
    sections: ["pulse", "crew", "smartstack", "workplan", "workloads", "gpus", "stream", "links", "digest"],
    streamFilter: ["task", "agent"],
    navHighlight: ["/gallery", "/chat"],
  },
  eoq: {
    id: "eoq",
    label: "EoBQ",
    icon: "E",
    accent: "oklch(0.65 0.15 25)",
    accentHue: 25,
    agents: ["creative-agent", "coding-agent"],
    sections: ["pulse", "crew", "smartstack", "workplan", "stream", "workloads", "gpus", "links", "digest"],
    streamFilter: ["task", "agent"],
    navHighlight: ["/chat", "/gallery", "/tasks"],
  },
};

export const LENS_IDS = Object.keys(LENS_CONFIG) as LensId[];
