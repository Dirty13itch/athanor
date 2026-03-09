import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { readJsonStorage, usePersistentState, writeJsonStorage } from "@/lib/state";

function PersistentHarness() {
  const [value, setValue, hydrated] = usePersistentState("test-key", "fallback");

  return (
    <div>
      <span data-testid="value">{value}</span>
      <span data-testid="hydrated">{String(hydrated)}</span>
      <button type="button" onClick={() => setValue("updated")}>
        Update
      </button>
    </div>
  );
}

describe("state helpers", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("falls back when storage contains invalid JSON", () => {
    window.localStorage.setItem("broken", "{");

    expect(readJsonStorage("broken", ["fallback"])).toEqual(["fallback"]);
  });

  it("writes JSON values to storage", () => {
    writeJsonStorage("json-key", { ok: true });

    expect(window.localStorage.getItem("json-key")).toBe('{"ok":true}');
  });

  it("hydrates persistent state from storage and persists updates", () => {
    window.localStorage.setItem("test-key", JSON.stringify("stored"));

    render(<PersistentHarness />);

    expect(screen.getByTestId("value")).toHaveTextContent("stored");
    expect(screen.getByTestId("hydrated")).toHaveTextContent("true");

    act(() => {
      screen.getByRole("button", { name: "Update" }).click();
    });

    expect(screen.getByTestId("value")).toHaveTextContent("updated");
    expect(window.localStorage.getItem("test-key")).toBe('"updated"');
  });
});
