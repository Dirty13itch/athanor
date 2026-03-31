import { randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import {
  agentThreadSchema,
  directChatSessionSchema,
  type AgentThread,
  type DirectChatSession,
  type OperatorContextItem,
  type OperatorContextSnapshot,
} from "@/lib/contracts";

interface OperatorContextFile {
  version: 1;
  updatedAt: string;
  sessions: Record<string, DirectChatSession>;
  threads: Record<string, AgentThread>;
}

const STORE_FILENAME = "operator-context.json";
const DEFAULT_STORE_PATH = path.join(process.cwd(), ".data", STORE_FILENAME);

let writeQueue: Promise<void> = Promise.resolve();

function nowIso(): string {
  return new Date().toISOString();
}

function resolveStorePath(): string {
  return process.env.DASHBOARD_OPERATOR_CONTEXT_PATH?.trim() || DEFAULT_STORE_PATH;
}

function defaultStore(): OperatorContextFile {
  return {
    version: 1,
    updatedAt: nowIso(),
    sessions: {},
    threads: {},
  };
}

function sortByUpdatedAtDesc<T extends { updatedAt: string }>(items: T[]): T[] {
  return [...items].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
}

function parseSessions(value: unknown): Record<string, DirectChatSession> {
  if (!value || typeof value !== "object") {
    return {};
  }

  const sessions: Record<string, DirectChatSession> = {};
  for (const [id, session] of Object.entries(value as Record<string, unknown>)) {
    const parsed = directChatSessionSchema.safeParse(session);
    if (parsed.success) {
      sessions[id] = parsed.data;
    }
  }
  return sessions;
}

function parseThreads(value: unknown): Record<string, AgentThread> {
  if (!value || typeof value !== "object") {
    return {};
  }

  const threads: Record<string, AgentThread> = {};
  for (const [id, thread] of Object.entries(value as Record<string, unknown>)) {
    const parsed = agentThreadSchema.safeParse(thread);
    if (parsed.success) {
      threads[id] = parsed.data;
    }
  }
  return threads;
}

async function readStoreFile(): Promise<OperatorContextFile> {
  const storePath = resolveStorePath();
  try {
    const raw = await readFile(storePath, "utf8");
    const parsed = JSON.parse(raw) as Partial<OperatorContextFile>;
    return {
      version: 1,
      updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : nowIso(),
      sessions: parseSessions(parsed.sessions),
      threads: parseThreads(parsed.threads),
    };
  } catch {
    return defaultStore();
  }
}

async function writeStoreFile(store: OperatorContextFile): Promise<void> {
  const storePath = resolveStorePath();
  await mkdir(path.dirname(storePath), { recursive: true });

  const tempPath = `${storePath}.${randomUUID()}.tmp`;
  await writeFile(tempPath, `${JSON.stringify(store, null, 2)}\n`, "utf8");
  await rename(tempPath, storePath);
}

function buildRecentContext(
  sessions: DirectChatSession[],
  threads: AgentThread[]
): OperatorContextItem[] {
  return sortByUpdatedAtDesc([
    ...sessions.map((session) => ({
      id: session.id,
      title: session.title,
      route: `/chat?session=${session.id}`,
      updatedAt: session.updatedAt,
      type: "direct_chat_session" as const,
    })),
    ...threads.map((thread) => ({
      id: thread.id,
      title: thread.title,
      route: `/agents?thread=${thread.id}&agent=${thread.agentId}`,
      updatedAt: thread.updatedAt,
      type: "agent_thread" as const,
    })),
  ]).slice(0, 10);
}

function toSnapshot(store: OperatorContextFile): OperatorContextSnapshot {
  const sessions = sortByUpdatedAtDesc(Object.values(store.sessions));
  const threads = sortByUpdatedAtDesc(Object.values(store.threads));

  return {
    source: "file",
    updatedAt: store.updatedAt,
    sessionCount: sessions.length,
    threadCount: threads.length,
    recentContext: buildRecentContext(sessions, threads),
    sessions,
    threads,
  };
}

async function mutateStore(
  updater: (store: OperatorContextFile) => OperatorContextFile
): Promise<OperatorContextSnapshot> {
  const next = writeQueue.then(async () => {
    const current = await readStoreFile();
    const updated = updater(current);
    updated.updatedAt = nowIso();
    await writeStoreFile(updated);
    return updated;
  });

  writeQueue = next.then(() => undefined, () => undefined);
  const store = await next;
  return toSnapshot(store);
}

export async function readOperatorContext(): Promise<OperatorContextSnapshot> {
  return toSnapshot(await readStoreFile());
}

export async function saveDirectChatSession(session: DirectChatSession): Promise<OperatorContextSnapshot> {
  const parsed = directChatSessionSchema.parse(session);
  return mutateStore((store) => ({
    ...store,
    sessions: {
      ...store.sessions,
      [parsed.id]: parsed,
    },
  }));
}

export async function deleteDirectChatSession(sessionId: string): Promise<OperatorContextSnapshot> {
  return mutateStore((store) => {
    const sessions = { ...store.sessions };
    delete sessions[sessionId];
    return {
      ...store,
      sessions,
    };
  });
}

export async function saveAgentThread(thread: AgentThread): Promise<OperatorContextSnapshot> {
  const parsed = agentThreadSchema.parse(thread);
  return mutateStore((store) => ({
    ...store,
    threads: {
      ...store.threads,
      [parsed.id]: parsed,
    },
  }));
}

export async function deleteAgentThread(threadId: string): Promise<OperatorContextSnapshot> {
  return mutateStore((store) => {
    const threads = { ...store.threads };
    delete threads[threadId];
    return {
      ...store,
      threads,
    };
  });
}

export async function __resetOperatorContextStoreForTests(): Promise<void> {
  writeQueue = Promise.resolve();
}
