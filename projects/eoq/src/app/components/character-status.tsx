"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";
import { getBreakingStage } from "@/types/game";

/**
 * Character status tooltip — shows detailed stats when clicking the portrait area.
 * Positioned near the character portrait.
 */
export function CharacterStatus({
  expanded,
  onToggle,
}: {
  expanded: boolean;
  onToggle: () => void;
}) {
  const session = useGameStore((s) => s.session);

  if (!session) return null;

  const presentChars = session.worldState.currentScene.presentCharacters;
  const charId = presentChars[0];
  if (!charId) return null;

  const char = session.characters[charId];
  if (!char) return null;

  const stage = getBreakingStage(char.resistance);
  const rel = char.relationship;
  const ep = char.emotionalProfile;

  return (
    <>
      {/* Clickable trigger area overlaid on the portrait region */}
      <button
        onClick={onToggle}
        className="fixed bottom-48 right-8 z-15 h-12 w-12 rounded-full border border-white/10 bg-black/40 text-xs text-white/30 transition-colors hover:border-amber-400/30 hover:text-amber-400/60"
        title="Character Info (I)"
      >
        i
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="fixed bottom-64 right-8 z-20 w-64 rounded-lg border border-white/10 bg-slate-900/95 p-4 backdrop-blur-sm"
          >
            {/* Header */}
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-amber-400">
                  {char.name}
                </h3>
                {char.title && (
                  <p className="text-[10px] text-white/30">{char.title}</p>
                )}
              </div>
              <span className={`text-[10px] font-semibold uppercase ${stageColor(stage)}`}>
                {stage}
              </span>
            </div>

            {/* Emotional State */}
            <div className="mb-3">
              <p className="mb-1 text-[10px] uppercase tracking-wider text-white/20">
                Emotion
              </p>
              <p className="text-xs text-white/60">
                {char.emotion.primary}
                {char.emotion.secondary && ` / ${char.emotion.secondary}`}
              </p>
            </div>

            {/* Relationship Bars */}
            <div className="mb-3 space-y-1.5">
              <p className="text-[10px] uppercase tracking-wider text-white/20">
                Relationship
              </p>
              <StatRow label="Trust" value={rel.trust} min={-100} max={100} color="blue" />
              <StatRow label="Respect" value={rel.respect} min={-100} max={100} color="green" />
              <StatRow label="Affection" value={rel.affection} min={-100} max={100} color="pink" />
              {rel.desire > 0 && <StatRow label="Desire" value={rel.desire} min={0} max={100} color="rose" />}
              {rel.fear > 0 && <StatRow label="Fear" value={rel.fear} min={0} max={100} color="red" />}
            </div>

            {/* Breaking System */}
            <div className="mb-3 space-y-1.5">
              <p className="text-[10px] uppercase tracking-wider text-white/20">
                Breaking
                {char.awakeningFired && (
                  <span className="ml-2 text-rose-400 normal-case tracking-normal">
                    ✦ Awakened
                  </span>
                )}
                {!char.awakeningFired && char.corruption >= 50 && (
                  <span className="ml-2 text-amber-400 normal-case tracking-normal">
                    ◈ Threshold Near
                  </span>
                )}
              </p>
              <StatRow
                label={`Resistance (max ${char.resistanceCeiling ?? 100})`}
                value={char.resistance}
                min={0}
                max={char.resistanceCeiling ?? 100}
                color="amber"
              />
              <StatRow label="Corruption" value={char.corruption} min={0} max={100} color="purple" />
              {char.currentEndingPath && (
                <p className="text-[9px] text-white/30 mt-1">
                  Path: <span className="text-white/50">{char.currentEndingPath.replace(/_/g, " ")}</span>
                </p>
              )}
            </div>

            {/* DNA Summary (queen characters only) */}
            {char.dna && (
              <div className="mb-3 space-y-1">
                <p className="text-[10px] uppercase tracking-wider text-white/20">DNA Profile</p>
                <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[9px] text-white/40">
                  <span>Desire: <span className="text-white/60">{char.dna.desireType}</span></span>
                  <span>Addiction: <span className="text-white/60">{char.dna.addictionSpeed}</span></span>
                  <span>Awakening: <span className="text-white/60">{char.dna.awakeningType.replace(/_/g, " ")}</span></span>
                  <span>Jealousy: <span className="text-white/60">{char.dna.jealousyType.replace(/_/g, " ")}</span></span>
                  <span>Switch: <span className="text-white/60">{char.dna.switchPotential}/10</span></span>
                  <span>Groups: <span className="text-white/60">{char.dna.groupSexAttitude}</span></span>
                </div>
                {char.stripperArc && (
                  <p className="text-[9px] text-rose-300/60 mt-1">
                    Stage: {char.stripperArc.stageName} · {char.stripperArc.club}
                  </p>
                )}
              </div>
            )}

            {/* Emotional Profile */}
            <div className="mb-3 space-y-1.5">
              <p className="text-[10px] uppercase tracking-wider text-white/20">
                Emotional Profile
              </p>
              <StatRow label="Fear" value={ep.fear} min={0} max={100} color="red" />
              <StatRow label="Defiance" value={ep.defiance} min={0} max={100} color="orange" />
              <StatRow label="Arousal" value={ep.arousal} min={0} max={100} color="rose" />
              <StatRow label="Submission" value={ep.submission} min={0} max={100} color="purple" />
              <StatRow label="Despair" value={ep.despair} min={0} max={100} color="slate" />
            </div>

            {/* Memories */}
            {rel.memories.length > 0 && (
              <div className="mb-3 space-y-1">
                <p className="text-[10px] uppercase tracking-wider text-white/20">
                  Memories ({rel.memories.length})
                </p>
                <div className="max-h-20 overflow-y-auto">
                  {rel.memories.slice(-3).map((mem, i) => (
                    <p key={i} className="text-[9px] leading-tight text-white/25">
                      {mem.emotionalImpact > 0 ? "+" : ""}{mem.emotionalImpact.toFixed(0)} — {mem.summary.slice(0, 80)}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* Vulnerabilities */}
            {char.vulnerabilities && Object.keys(char.vulnerabilities).length > 0 && (
              <div className="space-y-1">
                <p className="text-[10px] uppercase tracking-wider text-white/20">
                  Vulnerabilities
                </p>
                <div className="flex flex-wrap gap-1">
                  {(Object.entries(char.vulnerabilities) as [string, number][]).map(
                    ([method, value]) => (
                      <span
                        key={method}
                        className={`rounded px-1.5 py-0.5 text-[9px] uppercase tracking-wider ${
                          value > 0.5
                            ? "bg-emerald-900/30 text-emerald-400/60"
                            : value > 0
                              ? "bg-white/5 text-white/30"
                              : "bg-red-900/20 text-red-400/40"
                        }`}
                      >
                        {method} {value > 0.5 ? "▲" : value < 0 ? "▼" : "─"}
                      </span>
                    )
                  )}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

function StatRow({
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
  const range = max - min;
  const pct = ((value - min) / range) * 100;

  const colorMap: Record<string, string> = {
    blue: "bg-blue-500/60",
    green: "bg-green-500/60",
    pink: "bg-pink-500/60",
    rose: "bg-rose-500/60",
    red: "bg-red-500/60",
    amber: "bg-amber-500/60",
    purple: "bg-purple-500/60",
    orange: "bg-orange-500/60",
    slate: "bg-slate-400/60",
  };

  return (
    <div className="flex items-center gap-2">
      <span className="w-16 text-[10px] text-white/30">{label}</span>
      <div className="h-1.5 flex-1 rounded-full bg-white/5">
        <div
          className={`h-full rounded-full transition-all ${colorMap[color] ?? "bg-white/30"}`}
          style={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
        />
      </div>
      <span className="w-8 text-right text-[10px] tabular-nums text-white/25">
        {value}
      </span>
    </div>
  );
}

function stageColor(stage: string): string {
  switch (stage) {
    case "defiant": return "text-red-400";
    case "struggling": return "text-orange-400";
    case "conflicted": return "text-yellow-400";
    case "yielding": return "text-emerald-400";
    case "surrendered": return "text-purple-400";
    case "broken": return "text-slate-400";
    default: return "text-white/40";
  }
}
