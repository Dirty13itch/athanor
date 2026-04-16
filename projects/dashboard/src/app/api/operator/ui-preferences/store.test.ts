import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  __resetUiPreferencesStoreForTests,
  readUiPreferences,
  saveUiPreferences,
} from "./store";

describe("operator ui preferences store", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_UI_PREFERENCES_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-ui-preferences-"));
    env.DASHBOARD_UI_PREFERENCES_PATH = path.join(tempDir, "ui-preferences.json");
    await __resetUiPreferencesStoreForTests();
  });

  afterEach(async () => {
    if (originalPath === undefined) {
      delete env.DASHBOARD_UI_PREFERENCES_PATH;
    } else {
      env.DASHBOARD_UI_PREFERENCES_PATH = originalPath;
    }

    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
      tempDir = "";
    }
  });

  it("persists operator UI preferences to disk", async () => {
    await saveUiPreferences({
      density: "compact",
      lastSelectedAgentId: "coding-agent",
      lastSelectedModelKey: "litellm::/models/qwen",
      dismissedHints: ["welcome"],
    });

    const snapshot = await readUiPreferences();

    expect(snapshot.source).toBe("file");
    expect(snapshot.preferences.density).toBe("compact");
    expect(snapshot.preferences.lastSelectedAgentId).toBe("coding-agent");
    expect(snapshot.preferences.dismissedHints).toEqual(["welcome"]);
  });
});
