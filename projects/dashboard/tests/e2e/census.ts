import fs from "node:fs";
import path from "node:path";

export interface RouteAuditRecord {
  id: string;
  title: string;
  kind: "route" | "support_surface";
  routePath: string;
  navigation: {
    inPrimaryNavigation: boolean;
    family: string | null;
    label: string | null;
    primary: boolean | null;
    mobile: boolean | null;
  };
  sourceFiles: {
    primary: string;
    supporting: string[];
  };
  coverage: {
    coverageStatus: string | null;
    localChecks: string[];
    liveChecks: string[];
    primaryControls: string[];
  };
  completionStatus: string;
  notes: string[];
}

export interface ApiAuditRecord {
  id: string;
  title: string;
  apiPath: string;
  family: string;
  sourceFile: string;
  methods: string[];
  responseMode: string;
  accessClass: string;
  consumerStatus: string;
  likelyConsumers: string[];
  coverage: {
    coverageStatus: string | null;
    localChecks: string[];
    liveChecks: string[];
  };
  completionStatus: string;
  notes: string[];
}

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const COMPLETION_DIRS = [
  path.join(REPO_ROOT, "reports", "completion-audit", "latest", "inventory"),
  path.join(REPO_ROOT, "docs", "atlas", "inventory", "completion"),
];

function readJson<T>(filename: string): T {
  for (const directory of COMPLETION_DIRS) {
    const filePath = path.join(directory, filename);
    if (!fs.existsSync(filePath)) {
      continue;
    }
    const text = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(text) as T;
  }

  throw new Error(
    `Missing completion-audit inventory ${filename}; checked ${COMPLETION_DIRS.join(", ")}`
  );
}

export function loadRouteAuditRecords(): RouteAuditRecord[] {
  return readJson<RouteAuditRecord[]>("dashboard-route-census.json");
}

export function loadSupportSurfaceRecords(): RouteAuditRecord[] {
  return readJson<RouteAuditRecord[]>("dashboard-support-surface-census.json");
}

export function loadApiAuditRecords(): ApiAuditRecord[] {
  return readJson<ApiAuditRecord[]>("dashboard-api-census.json");
}
