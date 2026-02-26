"use client";

import { createContext, useContext, useCallback, useEffect, useState, type ReactNode } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { LENS_CONFIG, type LensId, type LensConfig } from "@/lib/lens";

interface LensContextValue {
  lens: LensId;
  config: LensConfig;
  setLens: (id: LensId) => void;
}

const LensContext = createContext<LensContextValue>({
  lens: "default",
  config: LENS_CONFIG.default,
  setLens: () => {},
});

export function useLens() {
  return useContext(LensContext);
}

export function LensProvider({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [lens, setLensState] = useState<LensId>("default");

  // Read lens from URL on mount
  useEffect(() => {
    const param = searchParams.get("lens");
    if (param && param in LENS_CONFIG) {
      setLensState(param as LensId);
    }
  }, [searchParams]);

  // Apply CSS custom properties when lens changes
  useEffect(() => {
    const cfg = LENS_CONFIG[lens];
    const root = document.documentElement;

    if (lens === "default") {
      root.removeAttribute("data-lens");
      root.style.removeProperty("--lens-accent");
      root.style.removeProperty("--lens-hue");
      // Restore default primary
      root.style.removeProperty("--primary");
      root.style.removeProperty("--ring");
    } else {
      root.setAttribute("data-lens", lens);
      root.style.setProperty("--lens-accent", cfg.accent);
      root.style.setProperty("--lens-hue", String(cfg.accentHue));
      // Override primary to recolor all shadcn components
      root.style.setProperty("--primary", cfg.accent);
      root.style.setProperty("--ring", cfg.accent);
    }

    return () => {
      root.removeAttribute("data-lens");
      root.style.removeProperty("--lens-accent");
      root.style.removeProperty("--lens-hue");
      root.style.removeProperty("--primary");
      root.style.removeProperty("--ring");
    };
  }, [lens]);

  const setLens = useCallback(
    (id: LensId) => {
      setLensState(id);
      const params = new URLSearchParams(searchParams.toString());
      if (id === "default") {
        params.delete("lens");
      } else {
        params.set("lens", id);
      }
      const qs = params.toString();
      router.replace(qs ? `?${qs}` : window.location.pathname, { scroll: false });
    },
    [searchParams, router]
  );

  return (
    <LensContext.Provider value={{ lens, config: LENS_CONFIG[lens], setLens }}>
      {children}
    </LensContext.Provider>
  );
}
