import { expect, type Page } from "@playwright/test";

export async function gotoRoute(page: Page, path: string, heading: RegExp | string) {
  await page.goto(path, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 3_000 }).catch(() => undefined);
  await expect(page.locator("h1")).toContainText(heading, { timeout: 15_000 });
}

export async function seedSavedGame(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "eoq-save",
      JSON.stringify({
        session: {
          id: "fixture-session",
          startedAt: Date.now() - 5 * 60 * 1000,
          lastPlayedAt: Date.now(),
          arcPosition: "prologue",
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
            inventory: ["royal-seal"],
            contentIntensity: 3,
          },
          characters: {
            isolde: {
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
          },
          dialogueHistory: [
            { speaker: "narrator", text: "Moonlight catches on the broken crown above the gate." },
            { speaker: "isolde", text: "You return to my court uninvited." },
            { speaker: "player", text: "I return because you still need something only I can offer." },
          ],
        },
        visitedScenes: ["courtyard"],
      }),
    );
  });
}
