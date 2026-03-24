"use client";

import { useState } from "react";
import { useGameStore } from "@/stores/game-store";
import { QUEENS } from "@/data/queens";
import { getBreakingStage } from "@/types/game";

const ARCHETYPE_COLORS: Record<string, string> = {
  warrior: "#3b82f6",
  defiant: "#3b82f6",
  sorceress: "#8b5cf6",
  priestess: "#8b5cf6",
  seductress: "#ec4899",
  ice: "#93c5fd",
  fire: "#f97316",
  shadow: "#6b21a8",
  sun: "#eab308",
  innocent: "#f9a8d4",
  scholar: "#10b981",
  merchant: "#78716c",
};

interface QueenSelectorProps {
  onConfirm: (queenIds: string[]) => void;
}

export function QueenSelector({ onConfirm }: QueenSelectorProps) {
  const mode = useGameStore((s) => s.queenSelectorMode);
  const setMode = useGameStore((s) => s.setQueenSelectorMode);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  if (!mode) return null;

  const minQueens = mode === "banquet" ? 3 : 2;
  const maxQueens = mode === "banquet" ? 5 : 2;
  const title = mode === "confrontation" ? "Call a Confrontation"
    : mode === "banquet" ? "Host a Banquet"
    : "Arrange a Rivalry Duel";

  function toggleQueen(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < maxQueens) {
        next.add(id);
      }
      return next;
    });
  }

  function handleConfirm() {
    if (selected.size >= minQueens) {
      onConfirm(Array.from(selected));
      setSelected(new Set());
      setMode(null);
    }
  }

  function handleCancel() {
    setSelected(new Set());
    setMode(null);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-2xl rounded-2xl border border-amber-900/30 bg-gray-950 p-6 shadow-2xl">
        <h2 className="text-xl font-bold text-amber-100" style={{ fontFamily: "'Cormorant Garamond', serif" }}>
          {title}
        </h2>
        <p className="mt-1 text-sm text-gray-400">
          Select {minQueens === maxQueens ? minQueens : `${minQueens}-${maxQueens}`} queens
          <span className="ml-2 text-amber-500/80">({selected.size} selected)</span>
        </p>

        <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
          {Object.entries(QUEENS).map(([id, queen]) => {
            const isSelected = selected.has(id);
            const stage = getBreakingStage(queen.resistance);
            const color = ARCHETYPE_COLORS[queen.archetype] ?? "#6b7280";

            return (
              <button
                key={id}
                onClick={() => toggleQueen(id)}
                className={`flex flex-col items-center gap-1 rounded-xl border p-3 text-center transition-all ${
                  isSelected
                    ? "border-amber-500 bg-amber-500/10 ring-1 ring-amber-500/50"
                    : "border-gray-800 bg-gray-900/50 hover:border-gray-600"
                }`}
              >
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold text-white"
                  style={{ backgroundColor: color }}
                >
                  {queen.name[0]}
                </div>
                <span className="text-xs font-medium text-gray-200 leading-tight">
                  {queen.name.split(" ")[0]}
                </span>
                <span className="text-[10px] text-gray-500">{stage}</span>
              </button>
            );
          })}
        </div>

        <div className="mt-5 flex justify-end gap-3">
          <button
            onClick={handleCancel}
            className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 transition-colors hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={selected.size < minQueens}
            className="rounded-lg bg-amber-600 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {mode === "confrontation" ? "Summon Them" : mode === "banquet" ? "Set the Table" : "Begin the Duel"}
          </button>
        </div>
      </div>
    </div>
  );
}
