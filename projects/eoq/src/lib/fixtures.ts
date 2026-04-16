import type { Persona } from "@/app/api/references/route";
import type { Character, DialogueTurn, PlayerChoice } from "@/types/game";

const PERSONA_STORE_KEY = "__ATHANOR_EOQ_FIXTURE_PERSONAS__";
const MEMORY_STORE_KEY = "__ATHANOR_EOQ_FIXTURE_MEMORIES__";

type FixtureMemory = {
  characterId: string;
  text: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
};

function svgDataUrl(label: string, accent: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900" preserveAspectRatio="xMidYMid slice"><rect width="1200" height="900" fill="#09090b"/><rect x="48" y="48" width="1104" height="804" rx="36" fill="#111827" stroke="${accent}" stroke-width="4"/><circle cx="930" cy="184" r="120" fill="${accent}" opacity="0.16"/><circle cx="270" cy="680" r="180" fill="${accent}" opacity="0.1"/><text x="80" y="138" fill="#f5f5f4" font-family="Georgia, serif" font-size="52">Empire of Broken Queens</text><text x="80" y="212" fill="${accent}" font-family="Arial, sans-serif" font-size="30" letter-spacing="8">FIXTURE MODE</text><text x="80" y="506" fill="#fafaf9" font-family="Arial, sans-serif" font-size="78" font-weight="700">${escapeXml(label)}</text><text x="80" y="578" fill="#d6d3d1" font-family="Arial, sans-serif" font-size="28">Deterministic placeholder asset for audit, smoke, and gameplay tests.</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function getGlobalStore<T>(key: string, create: () => T): T {
  const target = globalThis as Record<string, unknown>;
  if (!(key in target)) {
    target[key] = create();
  }
  return target[key] as T;
}

function initialPersonas(): Persona[] {
  return [
    {
      id: "queens-isolde-fixture",
      name: "Isolde",
      category: "queens",
      folder: "fixture-isolde",
      photos: ["isolde-reference-01.jpg"],
      createdAt: "2026-03-10T02:00:00.000Z",
    },
    {
      id: "custom-vela-fixture",
      name: "Vela",
      category: "custom",
      folder: "fixture-vela",
      photos: ["vela-reference-01.jpg", "vela-reference-02.jpg"],
      createdAt: "2026-03-10T02:10:00.000Z",
    },
  ];
}

function initialMemories(): FixtureMemory[] {
  return [
    {
      characterId: "isolde",
      text: "The player refused to kneel and spoke to Isolde as an equal.",
      timestamp: Date.now() - 60 * 60 * 1000,
      metadata: { scene: "Ashenmoor Keep", intent: "defiance" },
    },
    {
      characterId: "isolde",
      text: "A softer approach briefly lowered Isolde's guard during the courtyard exchange.",
      timestamp: Date.now() - 15 * 60 * 1000,
      metadata: { scene: "Courtyard", intent: "genuine_concern" },
    },
  ];
}

export function getFixturePersonas(): Persona[] {
  return getGlobalStore(PERSONA_STORE_KEY, initialPersonas);
}

export function createFixturePersona(name: string, category: Persona["category"]): Persona {
  const personas = getFixturePersonas();
  const sanitized = name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const persona: Persona = {
    id: `${category}-${sanitized}-${personas.length + 1}`,
    name,
    category,
    folder: `${category}-${sanitized}`,
    photos: [],
    createdAt: new Date().toISOString(),
  };
  personas.push(persona);
  return persona;
}

export function deleteFixturePersona(id: string): boolean {
  const personas = getFixturePersonas();
  const index = personas.findIndex((persona) => persona.id === id);
  if (index === -1) {
    return false;
  }
  personas.splice(index, 1);
  return true;
}

export function addFixturePersonaPhoto(id: string, filename: string): string | null {
  const personas = getFixturePersonas();
  const persona = personas.find((entry) => entry.id === id);
  if (!persona) {
    return null;
  }
  const safeName = filename.replace(/[^a-zA-Z0-9._-]/g, "_");
  if (!persona.photos.includes(safeName)) {
    persona.photos.push(safeName);
  }
  return safeName;
}

export function removeFixturePersonaPhoto(id: string, filename: string): boolean {
  const personas = getFixturePersonas();
  const persona = personas.find((entry) => entry.id === id);
  if (!persona) {
    return false;
  }
  const previousLength = persona.photos.length;
  persona.photos = persona.photos.filter((entry) => entry !== filename);
  return persona.photos.length !== previousLength;
}

export function getFixtureGalleryImages() {
  return [
    {
      promptId: "fixture-prompt-isolde",
      filename: "isolde-portrait-fixture.png",
      subfolder: "EoBQ/character",
      type: "portrait" as const,
      character: "Isolde",
      imageUrl: svgDataUrl("Isolde Portrait", "#f43f5e"),
      timestamp: 1741572000000,
    },
    {
      promptId: "fixture-prompt-seraphine",
      filename: "seraphine-portrait-fixture.png",
      subfolder: "EoBQ/character",
      type: "portrait" as const,
      character: "Seraphine",
      imageUrl: svgDataUrl("Seraphine Portrait", "#8b5cf6"),
      timestamp: 1741575600000,
    },
    {
      promptId: "fixture-prompt-throne-room",
      filename: "throne-room-fixture.png",
      subfolder: "EoBQ/scene",
      type: "scene" as const,
      character: null,
      imageUrl: svgDataUrl("Throne Room Scene", "#f59e0b"),
      timestamp: 1741579200000,
    },
  ];
}

export function getFixtureChoices(character?: Character): PlayerChoice[] {
  const name = character?.name ?? "the queen";
  return [
    {
      text: `I did not come to threaten ${name}; I came to understand what they need.`,
      intent: "genuine_concern",
      effects: { trust: 6, respect: 4 },
    },
    {
      text: `Keep the mask if you must. I can still see the fear behind it.`,
      intent: "psychological_pressure",
      breakingMethod: "psychological",
      effects: { fear: 7, resistance: -5, respect: 2 },
    },
    {
      text: "Step closer, then. Let us see which of us yields first.",
      intent: "seductive_escalation",
      breakingMethod: "social",
      effects: { desire: 8, resistance: -4, corruption: 2 },
    },
  ];
}

export function getFixtureMemories(characterId: string) {
  const store = getGlobalStore(MEMORY_STORE_KEY, initialMemories);
  return store.filter((memory) => memory.characterId === characterId);
}

export function addFixtureMemory(entry: FixtureMemory) {
  const store = getGlobalStore(MEMORY_STORE_KEY, initialMemories);
  store.unshift(entry);
}

export function buildFixtureOpenAiStream(text: string): string {
  const chunks = text.match(/.{1,32}/g) ?? [text];
  const body = chunks
    .map((chunk) =>
      `data: ${JSON.stringify({
        id: "fixture-chat",
        object: "chat.completion.chunk",
        created: 1741572000,
        model: "fixture-reasoning",
        choices: [{ index: 0, delta: { content: chunk }, finish_reason: null }],
      })}\n\n`
    )
    .join("");

  const done = `data: ${JSON.stringify({
    id: "fixture-chat",
    object: "chat.completion.chunk",
    created: 1741572000,
    model: "fixture-reasoning",
    choices: [{ index: 0, delta: {}, finish_reason: "stop" }],
  })}\n\ndata: [DONE]\n\n`;

  return `${body}${done}`;
}

export function buildFixtureDialogueReply(character?: Character, recentHistory: DialogueTurn[] = []): string {
  const name = character?.name ?? "the queen";
  const lastPlayerTurn = [...recentHistory].reverse().find((turn) => turn.speaker === "player");
  const reference = lastPlayerTurn?.text ? `You said: "${lastPlayerTurn.text}". ` : "";
  return `${reference}*${name} studies you in silence before answering.* You are still in control of the scene, but the tension has shifted. Choose whether to press harder, build trust, or step back and watch what changes.`;
}

export function getFixtureGeneratedImage(label: string, accent = "#f59e0b"): string {
  return svgDataUrl(label, accent);
}
