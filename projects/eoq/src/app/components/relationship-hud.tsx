"use client";

import { useGameStore } from "@/stores/game-store";
import { getBreakingStage } from "@/types/game";

const STAGE_COLORS: Record<string, string> = {
  defiant: "text-red-400",
  struggling: "text-orange-400",
  conflicted: "text-yellow-400",
  yielding: "text-amber-300",
  surrendered: "text-emerald-400",
  broken: "text-purple-400",
};

const STAGE_LABELS: Record<string, string> = {
  defiant: "Defiant",
  struggling: "Struggling",
  conflicted: "Conflicted",
  yielding: "Yielding",
  surrendered: "Surrendered",
  broken: "Broken",
};

export function RelationshipHUD() {
  const session = useGameStore((s) => s.session);
  if (!session) return null;

  const presentIds = session.worldState.currentScene.presentCharacters;
  if (presentIds.length === 0) return null;

  return (
    <div className="fixed right-0 top-14 z-20 p-3">
      <div className="flex flex-col gap-2">
        {presentIds.map((charId) => {
          const char = session.characters[charId];
          if (!char) return null;

          const stage = getBreakingStage(char.resistance);
          const stageColor = STAGE_COLORS[stage] ?? "text-white/40";
          const stageLabel = STAGE_LABELS[stage] ?? stage;

          return (
            <div
              key={charId}
              className="w-44 rounded border border-white/10 bg-black/70 p-2.5 backdrop-blur-sm"
            >
              {/* Name and stage */}
              <div className="mb-1.5 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-amber-400/80">
                  {char.name}
                </span>
                <span className={`text-[10px] uppercase tracking-wider ${stageColor}`}>
                  {stageLabel}
                </span>
              </div>

              {/* Relationship bars */}
              <div className="flex flex-col gap-1">
                <StatBar label="Trust" value={char.relationship.trust} min={-100} max={100} color="bg-blue-500" />
                <StatBar label="Respect" value={char.relationship.respect} min={-100} max={100} color="bg-amber-500" />
                <StatBar label="Affection" value={char.relationship.affection} min={-100} max={100} color="bg-pink-500" />
                {char.relationship.desire > 0 && (
                  <StatBar label="Desire" value={char.relationship.desire} min={0} max={100} color="bg-rose-500" />
                )}
                {char.relationship.fear > 0 && (
                  <StatBar label="Fear" value={char.relationship.fear} min={0} max={100} color="bg-purple-500" />
                )}
              </div>

              {/* Resistance bar */}
              <div className="mt-1.5 border-t border-white/5 pt-1.5">
                <StatBar label="Resistance" value={char.resistance} min={0} max={100} color="bg-red-500" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatBar({
  label,
  value,
  min,
  max,
  color,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  color: string;
}) {
  // Normalize to 0-100%
  const range = max - min;
  const pct = Math.max(0, Math.min(100, ((value - min) / range) * 100));
  // For bipolar stats (-100 to 100), show from center
  const isBipolar = min < 0;

  return (
    <div className="flex items-center gap-1.5">
      <span className="w-14 text-[9px] uppercase tracking-wider text-white/30">
        {label}
      </span>
      <div className="relative h-1 flex-1 overflow-hidden rounded-full bg-white/10">
        {isBipolar ? (
          <>
            {/* Center mark */}
            <div className="absolute left-1/2 top-0 h-full w-px bg-white/20" />
            {/* Bar from center */}
            {value >= 0 ? (
              <div
                className={`absolute left-1/2 top-0 h-full rounded-r-full ${color}`}
                style={{ width: `${(value / max) * 50}%` }}
              />
            ) : (
              <div
                className={`absolute top-0 h-full rounded-l-full ${color} opacity-60`}
                style={{
                  right: "50%",
                  width: `${(Math.abs(value) / Math.abs(min)) * 50}%`,
                }}
              />
            )}
          </>
        ) : (
          <div
            className={`absolute left-0 top-0 h-full rounded-full ${color}`}
            style={{ width: `${pct}%` }}
          />
        )}
      </div>
      <span className="w-6 text-right text-[9px] tabular-nums text-white/30">
        {value}
      </span>
    </div>
  );
}
