"use client";

import { useEffect, useState } from "react";
import { QUEENS, QUEEN_ORDER } from "@/data/queens";
import type { Queen } from "@/types/game";

interface CustomQueenEntry extends Record<string, unknown> {
  personaId: string;
  photoCount: number;
  name: string;
  title: string;
  archetype: string;
  personality: Record<string, number>;
  resistance: number;
  speechStyle: string;
}

interface QueenRosterProps {
  onSelect: (queenId: string) => void;
  onBack: () => void;
}

export function QueenRoster({ onSelect, onBack }: QueenRosterProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [customQueens, setCustomQueens] = useState<CustomQueenEntry[]>([]);

  useEffect(() => {
    fetch("/api/queens/custom")
      .then((r) => r.json())
      .then((data) => setCustomQueens(data))
      .catch(() => {});
  }, []);

  const hovered = hoveredId
    ? QUEENS[hoveredId] ?? customQueens.find((q) => q.personaId === hoveredId)
    : null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center bg-black/95">
      {/* Header */}
      <div className="mt-8 text-center">
        <p className="text-[10px] uppercase tracking-[0.5em] text-white/20">
          Choose your audience
        </p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight text-amber-400">
          The Queen&apos;s Council
        </h2>
        <p className="mt-1 text-xs text-white/30">
          21 queens. Each one unique. Each one breakable.
        </p>
      </div>

      {/* Grid + Detail */}
      <div className="mt-6 flex w-full max-w-5xl flex-1 gap-6 overflow-hidden px-6">
        {/* Queen grid */}
        <div className="flex-1 overflow-y-auto pr-2">
          <div className="grid grid-cols-3 gap-2">
            {QUEEN_ORDER.map((id) => {
              const queen = QUEENS[id];
              return (
                <button
                  key={id}
                  onClick={() => onSelect(id)}
                  onMouseEnter={() => setHoveredId(id)}
                  onMouseLeave={() =>
                    setHoveredId((prev) => (prev === id ? prev : prev))
                  }
                  className={`group rounded border px-3 py-2.5 text-left transition-all ${
                    hoveredId === id
                      ? "border-amber-400/50 bg-amber-900/20"
                      : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10"
                  }`}
                >
                  <p className="text-sm font-medium text-amber-400/90 group-hover:text-amber-400">
                    {queen.name}
                  </p>
                  <p className="text-[10px] text-white/40">{queen.title}</p>
                </button>
              );
            })}
          </div>

          {/* Custom queens from Reference Library */}
          {customQueens.length > 0 && (
            <>
              <div className="mt-4 mb-2 h-px bg-white/10" />
              <p className="mb-2 text-[10px] uppercase tracking-widest text-violet-400/60">
                Custom Queens ({customQueens.length})
              </p>
              <div className="grid grid-cols-3 gap-2">
                {customQueens.map((cq) => (
                  <button
                    key={cq.personaId}
                    onClick={() => onSelect(`custom:${cq.personaId}`)}
                    onMouseEnter={() => setHoveredId(cq.personaId)}
                    className={`group rounded border px-3 py-2.5 text-left transition-all ${
                      hoveredId === cq.personaId
                        ? "border-violet-400/50 bg-violet-900/20"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10"
                    }`}
                  >
                    <p className="text-sm font-medium text-violet-400/90 group-hover:text-violet-400">
                      {cq.name}
                    </p>
                    <p className="text-[10px] text-white/40">{cq.title}</p>
                    <p className="text-[9px] text-white/20">{cq.photoCount} reference photos</p>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Detail panel */}
        <div className="w-72 shrink-0 overflow-y-auto rounded border border-white/10 bg-white/5 p-4">
          {hovered ? (
            <>
              <h3 className={`text-lg font-semibold ${"id" in hovered ? "text-amber-400" : "text-violet-400"}`}>
                {hovered.name}
              </h3>
              <p className="text-xs text-white/50">{hovered.title}</p>

              <div className="mt-3 h-px bg-white/10" />

              {/* Archetype */}
              <p className="mt-3 text-[10px] uppercase tracking-widest text-white/30">
                Archetype
              </p>
              <p className="text-sm text-white/70">{hovered.archetype}</p>

              {/* Key personality traits */}
              <p className="mt-3 text-[10px] uppercase tracking-widest text-white/30">
                Personality
              </p>
              <div className="mt-1 space-y-1">
                {Object.entries(hovered.personality)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .slice(0, 3)
                  .map(([trait, value]) => (
                    <div key={trait} className="flex items-center gap-2">
                      <span className="w-16 text-[10px] capitalize text-white/50">
                        {trait}
                      </span>
                      <div className="h-1 flex-1 rounded-full bg-white/10">
                        <div
                          className="h-full rounded-full bg-amber-400/60"
                          style={{ width: `${(value as number) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
              </div>

              {/* Breaking state */}
              <p className="mt-3 text-[10px] uppercase tracking-widest text-white/30">
                Resistance
              </p>
              <div className="mt-1 flex items-center gap-2">
                <div className="h-1.5 flex-1 rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-red-500/70"
                    style={{ width: `${hovered.resistance}%` }}
                  />
                </div>
                <span className="text-xs text-white/40">
                  {hovered.resistance}
                </span>
              </div>

              {/* Speech style preview */}
              <p className="mt-3 text-[10px] uppercase tracking-widest text-white/30">
                Voice
              </p>
              <p className="mt-1 text-[11px] italic leading-relaxed text-white/50">
                &ldquo;{hovered.speechStyle.split(".")[0]}.&rdquo;
              </p>

              {/* Start button */}
              <button
                onClick={() =>
                  "id" in hovered
                    ? onSelect((hovered as Queen).id)
                    : onSelect(`custom:${(hovered as CustomQueenEntry).personaId}`)
                }
                className={`mt-4 w-full rounded border py-2 text-sm transition-colors ${
                  "id" in hovered
                    ? "border-amber-400/40 bg-amber-900/20 text-amber-400 hover:bg-amber-900/40"
                    : "border-violet-400/40 bg-violet-900/20 text-violet-400 hover:bg-violet-900/40"
                }`}
              >
                Request Audience
              </button>
            </>
          ) : (
            <div className="flex h-full items-center justify-center">
              <p className="text-center text-xs text-white/30">
                Hover over a queen to see her profile
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Footer actions */}
      <div className="flex items-center gap-4 pb-6 pt-4">
        <button
          onClick={onBack}
          className="rounded border border-white/20 bg-black/40 px-6 py-2 text-sm text-white/50 transition-colors hover:border-white/30 hover:text-white/70"
        >
          Back
        </button>
        <a
          href="/references"
          className="rounded border border-violet-400/30 bg-black/40 px-6 py-2 text-sm text-violet-400/70 transition-colors hover:border-violet-400/50 hover:text-violet-400"
        >
          Reference Library — Upload Photos &amp; Create Queens
        </a>
      </div>
    </div>
  );
}
