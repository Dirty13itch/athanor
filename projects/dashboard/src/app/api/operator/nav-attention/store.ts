import { randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import {
  navAttentionPersistenceStateSchema,
  type NavAttentionPersistenceState,
  type NavAttentionSnapshot,
} from "@/lib/contracts";

interface NavAttentionStoreFile {
  version: 1;
  updatedAt: string;
  state: NavAttentionPersistenceState;
}

const STORE_FILENAME = "nav-attention.json";
const DEFAULT_STORE_PATH = path.join(process.cwd(), ".data", STORE_FILENAME);
const FALLBACK_STORE_PATH = path.join(os.tmpdir(), "athanor-dashboard", STORE_FILENAME);

let writeQueue: Promise<void> = Promise.resolve();

function nowIso(): string {
  return new Date().toISOString();
}

function resolveCandidateStorePaths(): string[] {
  const configuredPath = process.env.DASHBOARD_NAV_ATTENTION_PATH?.trim();
  if (configuredPath) {
    return [configuredPath, FALLBACK_STORE_PATH];
  }

  return [DEFAULT_STORE_PATH, FALLBACK_STORE_PATH];
}

function isRetryableFilesystemError(error: unknown): boolean {
  const code = typeof error === "object" && error && "code" in error ? String((error as { code?: string }).code) : "";
  return code === "EACCES" || code === "EPERM" || code === "EROFS";
}

function defaultStore(): NavAttentionStoreFile {
  return {
    version: 1,
    updatedAt: nowIso(),
    state: {},
  };
}

async function readStoreFile(): Promise<NavAttentionStoreFile> {
  for (const storePath of resolveCandidateStorePaths()) {
    try {
      const raw = await readFile(storePath, "utf8");
      const parsed = JSON.parse(raw) as Partial<NavAttentionStoreFile>;
      return {
        version: 1,
        updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : nowIso(),
        state: navAttentionPersistenceStateSchema.parse(parsed.state ?? {}),
      };
    } catch {
      continue;
    }
  }

  return defaultStore();
}

async function writeStoreFile(store: NavAttentionStoreFile): Promise<void> {
  let lastError: unknown = null;

  for (const storePath of resolveCandidateStorePaths()) {
    try {
      await mkdir(path.dirname(storePath), { recursive: true });
      const tempPath = `${storePath}.${randomUUID()}.tmp`;
      await writeFile(tempPath, `${JSON.stringify(store, null, 2)}\n`, "utf8");
      await rename(tempPath, storePath);
      return;
    } catch (error) {
      lastError = error;
      if (!isRetryableFilesystemError(error)) {
        throw error;
      }
    }
  }

  throw lastError instanceof Error ? lastError : new Error(`Failed to persist ${STORE_FILENAME}`);
}

function toSnapshot(store: NavAttentionStoreFile): NavAttentionSnapshot {
  return {
    source: "file",
    updatedAt: store.updatedAt,
    routeCount: Object.keys(store.state).length,
    state: store.state,
  };
}

async function mutateStore(
  updater: (store: NavAttentionStoreFile) => NavAttentionStoreFile
): Promise<NavAttentionSnapshot> {
  const next = writeQueue.then(async () => {
    const current = await readStoreFile();
    const updated = updater(current);
    updated.updatedAt = nowIso();
    updated.state = navAttentionPersistenceStateSchema.parse(updated.state);
    await writeStoreFile(updated);
    return updated;
  });

  writeQueue = next.then(() => undefined, () => undefined);
  return toSnapshot(await next);
}

export async function readNavAttentionState(): Promise<NavAttentionSnapshot> {
  return toSnapshot(await readStoreFile());
}

export async function saveNavAttentionState(
  state: NavAttentionPersistenceState
): Promise<NavAttentionSnapshot> {
  const parsed = navAttentionPersistenceStateSchema.parse(state);
  return mutateStore((store) => ({
    ...store,
    state: parsed,
  }));
}

export async function __resetNavAttentionStoreForTests(): Promise<void> {
  writeQueue = Promise.resolve();
}
