"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";
import { SCENES } from "@/data/scenes";
import { checkCondition } from "@/data/narrative";

interface SceneMapProps {
  open: boolean;
  onClose: () => void;
  onNavigate: (sceneId: string) => void;
}

/** Scene positions for the map layout (relative percentages) */
const SCENE_POSITIONS: Record<string, { x: number; y: number }> = {
  courtyard: { x: 30, y: 30 },
  "throne-room": { x: 65, y: 15 },
  "throne-close": { x: 80, y: 30 },
  tavern: { x: 15, y: 55 },
  undercroft: { x: 30, y: 75 },
  "crimson-gate": { x: 55, y: 75 },
  "oracle-spire": { x: 75, y: 60 },
  "vision-chamber": { x: 85, y: 75 },
};

const SCENE_SHORT_NAMES: Record<string, string> = {
  courtyard: "Courtyard",
  "throne-room": "Throne Room",
  "throne-close": "Before Throne",
  tavern: "Broken Antler",
  undercroft: "Undercroft",
  "crimson-gate": "Crimson Gate",
  "oracle-spire": "Oracle's Spire",
  "vision-chamber": "Vision Chamber",
};

/** Connection lines between scenes */
const CONNECTIONS: Array<{ from: string; to: string }> = [
  { from: "courtyard", to: "throne-room" },
  { from: "courtyard", to: "tavern" },
  { from: "courtyard", to: "undercroft" },
  { from: "courtyard", to: "crimson-gate" },
  { from: "throne-room", to: "throne-close" },
  { from: "tavern", to: "undercroft" },
  { from: "undercroft", to: "crimson-gate" },
  { from: "crimson-gate", to: "oracle-spire" },
  { from: "oracle-spire", to: "vision-chamber" },
];

export function SceneMap({ open, onClose, onNavigate }: SceneMapProps) {
  const session = useGameStore((s) => s.session);
  const visitedScenes = useGameStore((s) => s.visitedScenes);

  if (!session) return null;

  const currentSceneId = session.worldState.currentScene.id;
  const flags = session.worldState.plotFlags;

  function getSceneStatus(sceneId: string): "current" | "visited" | "available" | "locked" | "unknown" {
    if (sceneId === currentSceneId) return "current";
    if (visitedScenes.has(sceneId)) return "visited";

    // Check if reachable from any visited scene
    for (const conn of CONNECTIONS) {
      const sourceId = conn.from === sceneId ? conn.to : conn.to === sceneId ? conn.from : null;
      if (!sourceId) continue;
      if (!visitedScenes.has(sourceId) && sourceId !== currentSceneId) continue;

      const sourceScene = SCENES[sourceId];
      if (!sourceScene) continue;
      const exit = sourceScene.exits.find((e) => e.targetSceneId === sceneId);
      if (!exit) continue;

      if (checkCondition(exit.condition, flags)) return "available";
      return "locked";
    }
    return "unknown";
  }

  const statusColors: Record<string, string> = {
    current: "border-amber-400 bg-amber-400/20 text-amber-400",
    visited: "border-white/30 bg-white/5 text-white/60",
    available: "border-emerald-400/40 bg-emerald-900/20 text-emerald-400/60",
    locked: "border-red-400/20 bg-red-900/10 text-red-400/40",
    unknown: "border-white/5 bg-white/[0.02] text-white/15",
  };

  const lineColors: Record<string, string> = {
    open: "stroke-white/15",
    locked: "stroke-red-400/10",
    current: "stroke-amber-400/30",
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[65] flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            onClick={(e) => e.stopPropagation()}
            className="relative h-[60vh] w-full max-w-2xl rounded-lg border border-white/10 bg-slate-900/95 p-6"
          >
            <h2 className="mb-2 text-center text-sm font-semibold uppercase tracking-wider text-amber-400/70">
              Ashenmoor
            </h2>
            <p className="mb-4 text-center text-[10px] text-white/20">
              Day {session.worldState.day} · {session.worldState.timeOfDay}
            </p>

            {/* Map area */}
            <div className="relative h-[calc(100%-80px)] w-full">
              {/* Connection lines */}
              <svg className="absolute inset-0 h-full w-full" style={{ overflow: "visible" }}>
                {CONNECTIONS.map((conn) => {
                  const fromPos = SCENE_POSITIONS[conn.from];
                  const toPos = SCENE_POSITIONS[conn.to];
                  if (!fromPos || !toPos) return null;

                  const fromStatus = getSceneStatus(conn.from);
                  const toStatus = getSceneStatus(conn.to);
                  const isActive =
                    fromStatus === "current" || toStatus === "current";
                  const isLocked =
                    toStatus === "locked" || toStatus === "unknown" ||
                    fromStatus === "locked" || fromStatus === "unknown";

                  const lineClass = isActive
                    ? lineColors.current
                    : isLocked
                      ? lineColors.locked
                      : lineColors.open;

                  return (
                    <line
                      key={`${conn.from}-${conn.to}`}
                      x1={`${fromPos.x}%`}
                      y1={`${fromPos.y}%`}
                      x2={`${toPos.x}%`}
                      y2={`${toPos.y}%`}
                      className={lineClass}
                      strokeWidth={isActive ? 1.5 : 1}
                      strokeDasharray={isLocked ? "4 4" : undefined}
                    />
                  );
                })}
              </svg>

              {/* Scene nodes */}
              {Object.entries(SCENE_POSITIONS).map(([sceneId, pos]) => {
                const status = getSceneStatus(sceneId);
                const scene = SCENES[sceneId];
                if (!scene) return null;
                const name = SCENE_SHORT_NAMES[sceneId] ?? scene.name;
                const hasCharacter = scene.presentCharacters.length > 0;

                return (
                  <button
                    key={sceneId}
                    onClick={() => {
                      if (status === "current") return;
                      // Only allow direct navigation from current scene's exits
                      const currentScene = SCENES[currentSceneId];
                      const exit = currentScene?.exits.find(
                        (e) => e.targetSceneId === sceneId
                      );
                      if (exit && checkCondition(exit.condition, flags)) {
                        onNavigate(sceneId);
                        onClose();
                      }
                    }}
                    className={`absolute -translate-x-1/2 -translate-y-1/2 rounded border px-2.5 py-1.5 text-center transition-all ${statusColors[status]} ${
                      status === "current" ? "scale-110 shadow-lg shadow-amber-400/10" : ""
                    }`}
                    style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
                    title={status === "locked" ? "Path not yet open" : scene.name}
                  >
                    <div className="text-[10px] font-semibold whitespace-nowrap">
                      {status === "unknown" ? "???" : name}
                    </div>
                    {hasCharacter && status !== "unknown" && (
                      <div className="text-[8px] opacity-60">
                        {scene.presentCharacters
                          .map((id) => session.characters[id]?.name ?? id)
                          .join(", ")}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 left-6 flex gap-4 text-[9px] text-white/20">
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-sm border border-amber-400 bg-amber-400/20" /> Current
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-sm border border-white/30 bg-white/5" /> Visited
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-sm border border-emerald-400/40 bg-emerald-900/20" /> Available
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-sm border border-red-400/20 bg-red-900/10" /> Locked
              </span>
            </div>

            <button
              onClick={onClose}
              className="absolute bottom-4 right-6 text-xs text-white/30 transition-colors hover:text-white/50"
            >
              Close (M)
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
