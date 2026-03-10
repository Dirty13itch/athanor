import { expect, test } from "@playwright/test";
import { gotoRoute } from "./helpers";

const choicePayload = {
  character: {
    id: "isolde",
    name: "Isolde",
    title: "The Usurper Queen",
    archetype: "ice",
    resistance: 84,
    corruption: 8,
    vulnerabilities: { psychological: 0.6, social: 0.8 },
    personality: {
      dominance: 0.8,
      warmth: 0.3,
      cunning: 0.9,
      loyalty: 0.4,
      cruelty: 0.5,
      sensuality: 0.7,
      humor: 0.4,
      ambition: 0.95,
    },
    relationship: {
      trust: 14,
      affection: 7,
      respect: 34,
      desire: 10,
      fear: 16,
      memories: [],
    },
    emotion: { primary: "calculating", intensity: 0.6 },
    emotionalProfile: {
      fear: 15,
      defiance: 80,
      arousal: 14,
      submission: 4,
      despair: 8,
    },
    speechStyle: "Measured and dangerous.",
    visualDescription: "Fixture portrait.",
    boundaries: ["Will not beg.", "Will not yield easily."],
  },
  worldState: {
    currentScene: {
      id: "courtyard",
      name: "Courtyard",
      description: "A moonlit courtyard framed by ruined stone.",
      visualPrompt: "Moonlit courtyard, ruined stone arches, dark fantasy.",
      presentCharacters: ["isolde"],
      exits: [{ label: "Walk to the keep", targetSceneId: "ashenmoor-keep" }],
    },
    timeOfDay: "night",
    day: 1,
    plotFlags: {},
    inventory: [],
    contentIntensity: 3,
  },
  recentHistory: [
    { speaker: "isolde", text: "You return to my court uninvited." },
    { speaker: "player", text: "I return because you still need something only I can offer." },
  ],
};

test("routes render without crashing", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: /Empire of Broken Queens/i })).toBeVisible();

  await gotoRoute(page, "/gallery", /Portrait Gallery/i);
  await gotoRoute(page, "/references", /Reference Library/i);
});

test("api smoke covers game, media, and references endpoints", async ({ request }) => {
  const gallery = await request.get("/api/gallery?limit=5");
  expect(gallery.ok()).toBeTruthy();
  await expect(gallery.json()).resolves.toMatchObject({ total: expect.any(Number), images: expect.any(Array) });

  const references = await request.get("/api/references");
  expect(references.ok()).toBeTruthy();
  const referenceItems = await references.json();
  expect(referenceItems).toEqual(expect.any(Array));
  expect(referenceItems.length).toBeGreaterThan(0);

  const referenceDetail = await request.get(`/api/references/${referenceItems[0].id}`);
  expect(referenceDetail.ok()).toBeTruthy();
  await expect(referenceDetail.json()).resolves.toMatchObject({ id: referenceItems[0].id });

  const choices = await request.post("/api/choices", { data: choicePayload });
  expect(choices.ok()).toBeTruthy();
  await expect(choices.json()).resolves.toMatchObject({ choices: expect.any(Array) });

  const memoryWrite = await request.post("/api/memory", {
    data: {
      characterId: "isolde",
      sessionId: "fixture-session",
      text: "The player stayed calm under pressure.",
      metadata: { scene: "Courtyard" },
    },
  });
  expect(memoryWrite.ok()).toBeTruthy();

  const memoryRead = await request.get("/api/memory?characterId=isolde&query=pressure&limit=3");
  expect(memoryRead.ok()).toBeTruthy();
  await expect(memoryRead.json()).resolves.toMatchObject({ memories: expect.any(Array) });

  const generate = await request.post("/api/generate", {
    data: { prompt: "dark fantasy portrait", type: "portrait" },
  });
  expect(generate.ok()).toBeTruthy();
  await expect(generate.json()).resolves.toMatchObject({ imageUrl: expect.stringContaining("data:image/svg+xml") });

  const narrate = await request.fetch("/api/narrate", {
    method: "POST",
    data: { worldState: choicePayload.worldState, recentHistory: choicePayload.recentHistory },
    headers: { Accept: "text/event-stream" },
  });
  expect(narrate.ok()).toBeTruthy();
  expect(narrate.headers()["content-type"]).toContain("text/event-stream");

  const chat = await request.fetch("/api/chat", {
    method: "POST",
    data: {
      character: choicePayload.character,
      worldState: choicePayload.worldState,
      recentHistory: choicePayload.recentHistory,
      playerInput: "Tell me what you are hiding.",
    },
    headers: { Accept: "text/event-stream" },
  });
  expect(chat.ok()).toBeTruthy();
  expect(chat.headers()["content-type"]).toContain("text/event-stream");
});

test("api validation degrades invalid payloads into 400s instead of 500s", async ({ request }) => {
  const invalidChoices = await request.post("/api/choices", { data: {} });
  expect(invalidChoices.status()).toBe(400);
  await expect(invalidChoices.json()).resolves.toMatchObject({ error: expect.any(String) });

  const invalidNarrate = await request.post("/api/narrate", { data: {} });
  expect(invalidNarrate.status()).toBe(400);
  await expect(invalidNarrate.json()).resolves.toMatchObject({ error: expect.any(String) });

  const invalidChat = await request.post("/api/chat", { data: {} });
  expect(invalidChat.status()).toBe(400);
  await expect(invalidChat.json()).resolves.toMatchObject({ error: expect.any(String) });
});
