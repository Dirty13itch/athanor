import { render } from "@testing-library/react";
import { createElement, isValidElement, type ComponentType, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

type ImportMetaWithGlob = ImportMeta & {
  glob: (pattern: string, options: { eager: true }) => Record<string, unknown>;
};

vi.mock("next/font/google", () => ({
  Inter: () => ({ variable: "--font-inter", className: "font-inter" }),
  Cormorant_Garamond: () => ({ variable: "--font-cormorant", className: "font-cormorant" }),
  Geist_Mono: () => ({ variable: "--font-geist-mono", className: "font-geist-mono" }),
}));

const SUPPORT_MODULES = (import.meta as ImportMetaWithGlob).glob("./**/{loading,error,global-error,not-found,layout}.tsx", {
  eager: true,
});
const MANIFEST_MODULES = (import.meta as ImportMetaWithGlob).glob("./**/manifest.ts", { eager: true });

afterEach(() => {
  vi.restoreAllMocks();
});

describe("app support surfaces", () => {
  for (const [modulePath, mod] of Object.entries(SUPPORT_MODULES)) {
    it(`loads ${modulePath}`, async () => {
      const surfaceModule = mod as { default?: (props?: unknown) => ReactNode | Promise<ReactNode> };
      expect(surfaceModule.default).toBeTypeOf("function");

      if (modulePath.endsWith("/layout.tsx")) {
        const element = await Promise.resolve(surfaceModule.default?.({
          children: <div>Fixture child</div>,
        }));
        expect(isValidElement(element)).toBe(true);
        return;
      }

      const Surface = surfaceModule.default as ComponentType<{
        error?: Error;
        reset?: () => void;
      }>;

      if (modulePath.endsWith("/error.tsx") || modulePath.endsWith("/global-error.tsx")) {
        const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
        render(
          createElement(Surface, {
            error: new Error("Fixture error"),
            reset: () => undefined,
          })
        );
        consoleError.mockRestore();
        return;
      }

      render(createElement(Surface));
    });
  }

  for (const [modulePath, mod] of Object.entries(MANIFEST_MODULES)) {
    it(`loads ${modulePath}`, () => {
      const manifestModule = mod as { default?: () => Record<string, unknown> };
      expect(manifestModule.default).toBeTypeOf("function");
      const manifest = manifestModule.default?.();
      expect(manifest).toBeTruthy();
      expect(manifest?.name).toBeTruthy();
      expect(Array.isArray(manifest?.icons)).toBe(true);
    });
  }
});
