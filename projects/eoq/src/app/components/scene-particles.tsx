"use client";

import { useMemo } from "react";
import { useGameStore } from "@/stores/game-store";

/**
 * Scene-appropriate floating particles — embers, dust motes, snowflakes, etc.
 * Pure CSS animation, no canvas or heavy rendering.
 */

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  duration: number;
  delay: number;
  drift: number;
}

const SCENE_PARTICLES: Record<string, { count: number; color: string; type: "float" | "fall" | "rise" }> = {
  courtyard: { count: 12, color: "bg-orange-400/20", type: "rise" },     // embers
  "throne-room": { count: 8, color: "bg-white/10", type: "float" },     // dust motes
  "throne-close": { count: 6, color: "bg-white/10", type: "float" },    // dust
  tavern: { count: 5, color: "bg-amber-400/10", type: "rise" },         // candle sparks
  undercroft: { count: 10, color: "bg-blue-400/10", type: "fall" },     // water drops
  "crimson-gate": { count: 15, color: "bg-red-400/15", type: "float" }, // void particles
  "oracle-spire": { count: 20, color: "bg-blue-300/15", type: "rise" }, // star fragments
  "vision-chamber": { count: 25, color: "bg-purple-300/15", type: "float" }, // mirror shards
};

function generateParticles(count: number): Particle[] {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: 1 + Math.random() * 3,
    duration: 8 + Math.random() * 12,
    delay: Math.random() * -20,
    drift: -15 + Math.random() * 30,
  }));
}

export function SceneParticles() {
  const session = useGameStore((s) => s.session);
  const sceneId = session?.worldState.currentScene.id ?? "";
  const config = SCENE_PARTICLES[sceneId];

  const particles = useMemo(
    () => (config ? generateParticles(config.count) : []),
    [config]
  );

  if (!config || particles.length === 0) return null;

  return (
    <div className="pointer-events-none fixed inset-0 z-[5] overflow-hidden">
      {particles.map((p) => (
        <div
          key={p.id}
          className={`absolute rounded-full ${config.color}`}
          style={{
            left: `${p.x}%`,
            top: config.type === "rise" ? "100%" : config.type === "fall" ? "-5%" : `${p.y}%`,
            width: `${p.size}px`,
            height: `${p.size}px`,
            animation: `particle-${config.type} ${p.duration}s linear ${p.delay}s infinite`,
            // @ts-expect-error CSS custom property
            "--drift": `${p.drift}px`,
          }}
        />
      ))}
    </div>
  );
}
