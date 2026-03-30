import { randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import {
  uiPreferencesSchema,
  type OperatorUiPreferencesSnapshot,
  type UiPreferences,
} from "@/lib/contracts";
import { DEFAULT_UI_PREFERENCES } from "@/lib/state";

interface UiPreferencesStoreFile {
  version: 1;
  updatedAt: string;
  preferences: UiPreferences;
}

const STORE_FILENAME = "ui-preferences.json";
const DEFAULT_STORE_PATH = path.join(process.cwd(), ".data", STORE_FILENAME);

let writeQueue: Promise<void> = Promise.resolve();

function nowIso(): string {
  return new Date().toISOString();
}

function resolveStorePath(): string {
  return process.env.DASHBOARD_UI_PREFERENCES_PATH?.trim() || DEFAULT_STORE_PATH;
}

function defaultStore(updatedAt = ""): UiPreferencesStoreFile {
  return {
    version: 1,
    updatedAt,
    preferences: { ...DEFAULT_UI_PREFERENCES },
  };
}

async function readStoreFile(): Promise<UiPreferencesStoreFile> {
  const storePath = resolveStorePath();
  try {
    const raw = await readFile(storePath, "utf8");
    const parsed = JSON.parse(raw) as Partial<UiPreferencesStoreFile>;
    return {
      version: 1,
      updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : "",
      preferences: uiPreferencesSchema.parse(parsed.preferences ?? DEFAULT_UI_PREFERENCES),
    };
  } catch {
    return defaultStore();
  }
}

async function writeStoreFile(store: UiPreferencesStoreFile): Promise<void> {
  const storePath = resolveStorePath();
  await mkdir(path.dirname(storePath), { recursive: true });
  const tempPath = `${storePath}.${randomUUID()}.tmp`;
  await writeFile(tempPath, `${JSON.stringify(store, null, 2)}\n`, "utf8");
  await rename(tempPath, storePath);
}

function toSnapshot(store: UiPreferencesStoreFile): OperatorUiPreferencesSnapshot {
  return {
    source: "file",
    updatedAt: store.updatedAt,
    preferences: store.preferences,
  };
}

async function mutateStore(
  updater: (store: UiPreferencesStoreFile) => UiPreferencesStoreFile
): Promise<OperatorUiPreferencesSnapshot> {
  const next = writeQueue.then(async () => {
    const current = await readStoreFile();
    const updated = updater(current);
    updated.updatedAt = nowIso();
    updated.preferences = uiPreferencesSchema.parse(updated.preferences);
    await writeStoreFile(updated);
    return updated;
  });

  writeQueue = next.then(() => undefined, () => undefined);
  return toSnapshot(await next);
}

export async function readUiPreferences(): Promise<OperatorUiPreferencesSnapshot> {
  return toSnapshot(await readStoreFile());
}

export async function saveUiPreferences(
  preferences: UiPreferences
): Promise<OperatorUiPreferencesSnapshot> {
  const parsed = uiPreferencesSchema.parse(preferences);
  return mutateStore((store) => ({
    ...store,
    preferences: parsed,
  }));
}

export async function __resetUiPreferencesStoreForTests(): Promise<void> {
  writeQueue = Promise.resolve();
}
