import { randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
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

let writeQueue: Promise<void> = Promise.resolve();

function nowIso(): string {
  return new Date().toISOString();
}

function resolveStorePath(): string {
  return process.env.DASHBOARD_NAV_ATTENTION_PATH?.trim() || DEFAULT_STORE_PATH;
}

function defaultStore(): NavAttentionStoreFile {
  return {
    version: 1,
    updatedAt: nowIso(),
    state: {},
  };
}

async function readStoreFile(): Promise<NavAttentionStoreFile> {
  const storePath = resolveStorePath();
  try {
    const raw = await readFile(storePath, "utf8");
    const parsed = JSON.parse(raw) as Partial<NavAttentionStoreFile>;
    return {
      version: 1,
      updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : nowIso(),
      state: navAttentionPersistenceStateSchema.parse(parsed.state ?? {}),
    };
  } catch {
    return defaultStore();
  }
}

async function writeStoreFile(store: NavAttentionStoreFile): Promise<void> {
  const storePath = resolveStorePath();
  await mkdir(path.dirname(storePath), { recursive: true });
  const tempPath = `${storePath}.${randomUUID()}.tmp`;
  await writeFile(tempPath, `${JSON.stringify(store, null, 2)}\n`, "utf8");
  await rename(tempPath, storePath);
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
