"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { CHARACTERS } from "@/data/characters";
import type { LegacyDaughter, PersonalityVector } from "@/types/game";

// ---------------------------------------------------------------------------
// Queen metadata for the selector — only queens with DNA
// ---------------------------------------------------------------------------

interface QueenOption {
  id: string;
  name: string;
  title: string;
  color: string;       // Tailwind border/text color class stem
  colorAccent: string;  // For bg hover
  shortDesc: string;
  visualSnippet: string;
}

const QUEEN_OPTIONS: QueenOption[] = Object.values(CHARACTERS)
  .filter((c) => !!c.dna)
  .map((c) => ({
    id: c.id,
    name: c.name,
    title: c.title ?? "",
    color: queenColor(c.id),
    colorAccent: queenAccent(c.id),
    shortDesc: c.speechStyle.split(".")[0] + ".",
    visualSnippet: c.visualDescription.split(".").slice(0, 2).join(".") + ".",
  }));

function queenColor(id: string): string {
  const map: Record<string, string> = {
    isolde: "rose-400",
    seraphine: "violet-400",
    mira: "amber-400",
    valeria: "amber-500",
    lilith: "red-400",
    mireille: "emerald-400",
  };
  return map[id] ?? "white";
}

function queenAccent(id: string): string {
  const map: Record<string, string> = {
    isolde: "rose-900/30",
    seraphine: "violet-900/30",
    mira: "amber-900/30",
    valeria: "amber-900/30",
    lilith: "red-900/30",
    mireille: "emerald-900/30",
  };
  return map[id] ?? "white/10";
}

// ---------------------------------------------------------------------------
// Inherited path options
// ---------------------------------------------------------------------------

type InheritedPath = "craves" | "fights" | "random";

const PATH_OPTIONS: { value: InheritedPath; label: string; desc: string }[] = [
  { value: "random",  label: "Fate Decides",  desc: "60% craves, 40% fights" },
  { value: "craves",  label: "Craves It",     desc: "She knows everything and wants more" },
  { value: "fights",  label: "Fights It",      desc: "She knows everything and resists — harder surrender" },
];

// ---------------------------------------------------------------------------
// Personality trait bar component
// ---------------------------------------------------------------------------

function TraitBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="w-20 text-right text-[11px] text-white/40">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
        <div
          className={`h-full rounded-full bg-${color}/60 transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-[10px] text-white/30">{pct}%</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// DNA trait display
// ---------------------------------------------------------------------------

function DNATag({ label, value }: { label: string; value: string | number }) {
  return (
    <span className="inline-block rounded border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-white/50">
      <span className="text-white/30">{label}:</span> {typeof value === "number" ? `${value}/10` : value}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

interface ForgeResponse {
  daughter: LegacyDaughter;
  comfyJobId: string | null;
  message: string;
}

export default function SoulForgePage() {
  const [selectedQueen, setSelectedQueen] = useState<string | null>(null);
  const [tasteDescriptor, setTasteDescriptor] = useState("");
  const [inheritedPath, setInheritedPath] = useState<InheritedPath>("random");
  const [isForging, setIsForging] = useState(false);
  const [result, setResult] = useState<ForgeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canForge = selectedQueen !== null && !isForging;

  const forge = useCallback(async () => {
    if (!selectedQueen) return;
    setIsForging(true);
    setError(null);
    setResult(null);

    try {
      const body: Record<string, unknown> = {
        motherId: selectedQueen,
        generation: 1,
        tasteDescriptor,
      };
      if (inheritedPath !== "random") {
        body.inheritedPath = inheritedPath;
      }

      const resp = await fetch("/api/soulforge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => null);
        throw new Error(data?.error ?? `HTTP ${resp.status}`);
      }

      const data: ForgeResponse = await resp.json();
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setIsForging(false);
    }
  }, [selectedQueen, tasteDescriptor, inheritedPath]);

  const resetForge = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  const daughter = result?.daughter;
  const motherColor = selectedQueen ? queenColor(selectedQueen) : "amber-400";

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <div className="border-b border-white/5 bg-black/40 px-6 py-4">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div>
            <h1 className="title-glow text-xl font-semibold tracking-tight text-amber-400">
              SoulForge
            </h1>
            <p className="text-[11px] text-white/30">
              Legacy Daughter Generation — DNA inheritance + mutation
            </p>
          </div>
          <Link
            href="/"
            className="rounded border border-white/10 bg-black/40 px-4 py-2 text-sm text-white/50 transition-colors hover:border-amber-400/30 hover:text-amber-400/60"
          >
            &larr; Back to Game
          </Link>
        </div>
      </div>

      <div className="mx-auto max-w-4xl px-6 py-8">
        {/* ================================================================= */}
        {/* Step 1: Select Mother Queen                                        */}
        {/* ================================================================= */}
        {!daughter && (
          <>
            <section>
              <h2 className="mb-1 text-xs font-semibold uppercase tracking-widest text-white/30">
                I. Choose a Mother Queen
              </h2>
              <p className="mb-4 text-[11px] text-white/20">
                Her DNA flows into the daughter — 60% inherited, 40% mutation.
              </p>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {QUEEN_OPTIONS.map((q) => {
                  const selected = selectedQueen === q.id;
                  return (
                    <button
                      key={q.id}
                      onClick={() => setSelectedQueen(selected ? null : q.id)}
                      className={`group relative overflow-hidden rounded border text-left transition-all duration-300 ${
                        selected
                          ? `border-${q.color}/60 bg-${q.colorAccent}`
                          : "border-white/10 bg-black/30 hover:border-white/20 hover:bg-black/50"
                      }`}
                    >
                      {/* Selection indicator */}
                      {selected && (
                        <div className={`absolute right-2 top-2 h-2 w-2 rounded-full bg-${q.color}`} />
                      )}

                      <div className="p-4">
                        <h3 className={`text-sm font-semibold ${selected ? `text-${q.color}` : "text-white/80"}`}>
                          {q.name}
                        </h3>
                        <p className={`text-[10px] italic ${selected ? `text-${q.color}/60` : "text-white/30"}`}>
                          {q.title}
                        </p>
                        <p className="mt-2 text-[11px] leading-relaxed text-white/40">
                          {q.visualSnippet}
                        </p>
                      </div>

                      {/* Bottom accent bar */}
                      <div
                        className={`h-0.5 transition-all duration-500 ${
                          selected ? `bg-${q.color}/40 w-full` : "w-0 bg-white/10"
                        }`}
                      />
                    </button>
                  );
                })}
              </div>
            </section>

            {/* Decorative divider */}
            <div className="my-8 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

            {/* ================================================================= */}
            {/* Step 2: Taste Descriptor                                           */}
            {/* ================================================================= */}
            <section>
              <h2 className="mb-1 text-xs font-semibold uppercase tracking-widest text-white/30">
                II. Taste Descriptor
                <span className="ml-2 font-normal normal-case tracking-normal text-white/15">(optional)</span>
              </h2>
              <p className="mb-3 text-[11px] text-white/20">
                Free-form text describing what traits you want amplified. The SoulForge interprets
                keywords like &ldquo;submissive&rdquo;, &ldquo;exhibitionist&rdquo;, &ldquo;pain&rdquo;,
                &ldquo;humiliation&rdquo;, &ldquo;slow&rdquo;, &ldquo;instant&rdquo;.
              </p>

              <textarea
                value={tasteDescriptor}
                onChange={(e) => setTasteDescriptor(e.target.value)}
                placeholder="e.g. submissive discovery, exhibitionist, slow addiction..."
                rows={2}
                className="w-full rounded border border-white/10 bg-black/40 px-4 py-3 text-sm text-white/80 placeholder:text-white/20 focus:border-amber-400/30 focus:outline-none"
              />
            </section>

            {/* Decorative divider */}
            <div className="my-8 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

            {/* ================================================================= */}
            {/* Step 3: Inherited Path                                             */}
            {/* ================================================================= */}
            <section>
              <h2 className="mb-1 text-xs font-semibold uppercase tracking-widest text-white/30">
                III. Inherited Path
              </h2>
              <p className="mb-3 text-[11px] text-white/20">
                Every Legacy Daughter knows the full history of her mother&apos;s breaking.
                She either craves the same fate — or fights it.
              </p>

              <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
                {PATH_OPTIONS.map((opt) => {
                  const active = inheritedPath === opt.value;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => setInheritedPath(opt.value)}
                      className={`flex-1 rounded border px-4 py-3 text-left transition-all ${
                        active
                          ? "border-amber-400/40 bg-amber-900/20"
                          : "border-white/10 bg-black/30 hover:border-white/20"
                      }`}
                    >
                      <span className={`text-sm font-medium ${active ? "text-amber-400" : "text-white/60"}`}>
                        {opt.label}
                      </span>
                      <p className="mt-0.5 text-[10px] text-white/30">{opt.desc}</p>
                    </button>
                  );
                })}
              </div>
            </section>

            {/* ================================================================= */}
            {/* Forge Button                                                       */}
            {/* ================================================================= */}
            <div className="mt-10 flex flex-col items-center gap-3">
              {/* Decorative divider */}
              <div className="h-px w-48 bg-gradient-to-r from-transparent via-amber-400/20 to-transparent" />

              <button
                onClick={forge}
                disabled={!canForge}
                className={`relative rounded border px-10 py-4 text-lg font-semibold tracking-wide transition-all duration-500 ${
                  canForge
                    ? "border-amber-400/50 bg-amber-900/30 text-amber-400 hover:border-amber-400/80 hover:bg-amber-900/50 hover:shadow-lg hover:shadow-amber-900/30"
                    : "cursor-not-allowed border-white/10 bg-black/20 text-white/20"
                }`}
              >
                {isForging ? (
                  <span className="flex items-center gap-3">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-amber-400/30 border-t-amber-400" />
                    Forging...
                  </span>
                ) : (
                  "Forge Daughter"
                )}
              </button>

              {!selectedQueen && (
                <p className="text-[10px] text-white/20">Select a mother queen to begin</p>
              )}

              {/* Decorative divider */}
              <div className="h-px w-48 bg-gradient-to-r from-transparent via-amber-400/20 to-transparent" />
            </div>

            {/* Error */}
            {error && (
              <div className="mt-6 rounded border border-red-400/30 bg-red-900/20 px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}
          </>
        )}

        {/* ================================================================= */}
        {/* Result: Generated Daughter                                         */}
        {/* ================================================================= */}
        {daughter && (
          <section className="animate-[fade-in-up_0.6s_ease-out]">
            {/* Daughter header */}
            <div className="mb-8 text-center">
              <p className="text-[10px] uppercase tracking-[0.4em] text-white/20">
                Legacy Daughter of {CHARACTERS[daughter.motherId]?.name ?? daughter.motherId}
              </p>
              <h2 className={`title-glow mt-1 text-4xl font-bold text-${motherColor}`}>
                {daughter.name}
              </h2>
              <p className="mt-2 text-xs text-white/30">
                Generation {daughter.generation} &middot;{" "}
                <span className={daughter.inheritedPath === "craves" ? "text-rose-400/60" : "text-violet-400/60"}>
                  {daughter.inheritedPath === "craves" ? "Craves the path" : "Fights the path"}
                </span>
              </p>
            </div>

            {/* Visual description */}
            <div className="mb-6 rounded border border-white/5 bg-black/30 p-5">
              <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-white/30">
                Visual Description
              </h3>
              <p className="text-sm leading-relaxed text-white/60 italic">
                {daughter.visualDescription}
              </p>
            </div>

            {/* Personality traits */}
            <div className="mb-6 rounded border border-white/5 bg-black/30 p-5">
              <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">
                Personality
              </h3>
              <div className="space-y-2">
                {(Object.entries(daughter.personality) as [keyof PersonalityVector, number][]).map(
                  ([trait, value]) => (
                    <TraitBar
                      key={trait}
                      label={trait.charAt(0).toUpperCase() + trait.slice(1)}
                      value={value}
                      color={motherColor}
                    />
                  )
                )}
              </div>
            </div>

            {/* DNA highlights */}
            <div className="mb-6 rounded border border-white/5 bg-black/30 p-5">
              <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">
                DNA Signature
              </h3>
              <div className="flex flex-wrap gap-2">
                <DNATag label="Desire" value={daughter.dna.desireType} />
                <DNATag label="Accelerator" value={daughter.dna.accelerator} />
                <DNATag label="Brake" value={daughter.dna.brake} />
                <DNATag label="Pain" value={daughter.dna.painTolerance} />
                <DNATag label="Humiliation" value={daughter.dna.humiliationEnjoyment} />
                <DNATag label="Exhibitionism" value={daughter.dna.exhibitionismLevel} />
                <DNATag label="Gag" value={daughter.dna.gagResponse} />
                <DNATag label="Awakening" value={daughter.dna.awakeningType} />
                <DNATag label="Addiction" value={daughter.dna.addictionSpeed} />
                <DNATag label="Jealousy" value={daughter.dna.jealousyType} />
                <DNATag label="Aftercare" value={daughter.dna.afterCareNeed} />
                <DNATag label="Switch" value={daughter.dna.switchPotential} />
                <DNATag label="Group" value={daughter.dna.groupSexAttitude} />
                <DNATag label="Blackmail" value={daughter.dna.blackmailNeed} />
                <DNATag label="Betrayal" value={daughter.dna.betrayalThreshold} />
              </div>

              {/* Longer text traits */}
              <div className="mt-4 space-y-2">
                {[
                  { label: "Moaning Style", value: daughter.dna.moaningStyle },
                  { label: "Tear Trigger", value: daughter.dna.tearTrigger },
                  { label: "Orgasm Style", value: daughter.dna.orgasmStyle },
                  { label: "Roleplay Affinity", value: daughter.dna.roleplayAffinity },
                  { label: "Voice DNA", value: daughter.dna.voiceDNA },
                ].map((item) => (
                  <div key={item.label}>
                    <span className="text-[10px] text-white/30">{item.label}:</span>
                    <p className="text-[11px] leading-relaxed text-white/50 italic">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* ComfyUI status */}
            {result && (
              <div className={`mb-6 rounded border px-4 py-3 text-[11px] ${
                result.comfyJobId
                  ? "border-emerald-400/20 bg-emerald-900/10 text-emerald-400/60"
                  : "border-white/5 bg-black/20 text-white/30"
              }`}>
                {result.message}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={resetForge}
                className="rounded border border-white/10 bg-black/40 px-6 py-2.5 text-sm text-white/50 transition-colors hover:border-amber-400/30 hover:text-amber-400/60"
              >
                Forge Another
              </button>
              <button
                onClick={() => {
                  resetForge();
                  forge();
                }}
                className={`rounded border border-${motherColor}/30 bg-black/40 px-6 py-2.5 text-sm text-${motherColor}/60 transition-colors hover:border-${motherColor}/60 hover:text-${motherColor}`}
              >
                Re-forge (Same Queen)
              </button>
            </div>
          </section>
        )}
      </div>

      {/* Footer credits */}
      <div className="py-6 text-center">
        <p className="text-[9px] text-white/10">SoulForge Engine v12 &middot; DNA Inheritance + Mutation</p>
      </div>
    </div>
  );
}
