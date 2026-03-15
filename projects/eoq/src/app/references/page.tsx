"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import type { Persona } from "../api/references/route";

const CATEGORY_LABEL: Record<string, string> = {
  queens: "Queens",
  custom: "Custom",
};

const CATEGORY_COLOR: Record<string, string> = {
  queens: "text-rose-400 border-rose-400/40",
  custom: "text-violet-400 border-violet-400/40",
};

export default function ReferencesPage() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [tab, setTab] = useState<"queens" | "custom">("queens");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [generating, setGenerating] = useState<string | null>(null);
  const [generatePrompt, setGeneratePrompt] = useState("");
  const [generateResult, setGenerateResult] = useState<string | null>(null);
  const [generateTarget, setGenerateTarget] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadTarget, setUploadTarget] = useState<string | null>(null);
  const [creatingQueen, setCreatingQueen] = useState<string | null>(null);
  const [queenGuidance, setQueenGuidance] = useState("");
  const [queenResult, setQueenResult] = useState<{ id: string; profile: Record<string, unknown> } | null>(null);
  const [dragTarget, setDragTarget] = useState<string | null>(null);

  const fetchPersonas = useCallback(async () => {
    setLoading(true);
    const res = await fetch("/api/references");
    if (res.ok) setPersonas(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => { fetchPersonas(); }, [fetchPersonas]);

  const createPersona = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    const res = await fetch("/api/references", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName.trim(), category: tab }),
    });
    if (res.ok) {
      const persona = await res.json();
      setPersonas((prev) => [...prev, persona]);
      setNewName("");
    }
    setCreating(false);
  };

  const deletePersona = async (id: string) => {
    if (!confirm("Delete this persona and all their photos?")) return;
    await fetch(`/api/references/${id}`, { method: "DELETE" });
    setPersonas((prev) => prev.filter((p) => p.id !== id));
  };

  const triggerUpload = (personaId: string) => {
    setUploadTarget(personaId);
    fileInputRef.current?.click();
  };

  const uploadFiles = async (personaId: string, files: FileList | File[]) => {
    for (const file of Array.from(files)) {
      if (!file.type.startsWith("image/")) continue;
      const form = new FormData();
      form.append("image", file);
      await fetch(`/api/references/${personaId}/photos`, { method: "POST", body: form });
    }
    await fetchPersonas();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !uploadTarget) return;
    await uploadFiles(uploadTarget, files);
    e.target.value = "";
    setUploadTarget(null);
  };

  const handleDrop = async (e: React.DragEvent, personaId: string) => {
    e.preventDefault();
    setDragTarget(null);
    const files = e.dataTransfer.files;
    if (files.length > 0) await uploadFiles(personaId, files);
  };

  const createQueenProfile = async (persona: Persona) => {
    setCreatingQueen(persona.id);
    setQueenResult(null);
    const res = await fetch(`/api/references/${persona.id}/create-queen`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customPrompt: queenGuidance || undefined }),
    });
    if (res.ok) {
      const profile = await res.json();
      setQueenResult({ id: persona.id, profile });
    }
    setCreatingQueen(null);
  };

  const deletePhoto = async (personaId: string, filename: string) => {
    await fetch(`/api/references/${personaId}/photos?filename=${encodeURIComponent(filename)}`, { method: "DELETE" });
    await fetchPersonas();
  };

  const generateWithLikeness = async (persona: Persona) => {
    if (!generatePrompt.trim()) {
      alert("Enter a prompt first.");
      return;
    }
    if (persona.photos.length === 0) {
      alert("Upload at least one reference photo first.");
      return;
    }
    setGenerating(persona.id);
    setGenerateResult(null);
    setGenerateTarget(persona.id);

    const referencePath = `/references/${persona.folder}/${persona.photos[0]}`;
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "pulid", prompt: generatePrompt, referencePath }),
    });

    if (res.ok) {
      const data = await res.json();
      setGenerateResult(data.imageUrl ?? null);
    }
    setGenerating(null);
  };

  const filtered = personas.filter((p) => p.category === tab);

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link href="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">← Back to game</Link>
        <h1 className="text-2xl font-bold text-white tracking-tight">Reference Library</h1>
        <span className="text-gray-600 text-sm ml-auto">PuLID face injection — powered by Flux</span>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-white/10 pb-3">
        {(["queens", "custom"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-all ${
              tab === t
                ? "bg-white/10 text-white"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {CATEGORY_LABEL[t]}
          </button>
        ))}
      </div>

      {/* Generate prompt (shared) */}
      <div className="mb-4 flex gap-3">
        <input
          type="text"
          value={generatePrompt}
          onChange={(e) => setGeneratePrompt(e.target.value)}
          placeholder="Generation prompt — e.g. 'cinematic portrait, dark fantasy, ornate armor, candlelight'"
          className="flex-1 bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-white/20"
        />
      </div>

      {/* Queen creation guidance */}
      <div className="mb-6 flex gap-3">
        <input
          type="text"
          value={queenGuidance}
          onChange={(e) => setQueenGuidance(e.target.value)}
          placeholder="Queen profile guidance (optional) — e.g. 'dominant ice archetype, high pain tolerance, French accent'"
          className="flex-1 bg-white/5 border border-amber-400/10 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-400/20"
        />
      </div>

      {/* Create persona */}
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && createPersona()}
          placeholder={`New ${CATEGORY_LABEL[tab]} persona name...`}
          className="flex-1 bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-white/20"
        />
        <button
          onClick={createPersona}
          disabled={creating || !newName.trim()}
          className="px-4 py-2 bg-white/10 hover:bg-white/15 text-white text-sm rounded transition-colors disabled:opacity-40"
        >
          {creating ? "Creating..." : "Add Persona"}
        </button>
      </div>

      {/* Personas grid */}
      {loading ? (
        <div className="text-gray-600 text-sm">Loading...</div>
      ) : filtered.length === 0 ? (
        <div className="text-gray-600 text-sm">
          No {CATEGORY_LABEL[tab].toLowerCase()} personas yet. Add one above.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {filtered.map((persona) => (
            <div
              key={persona.id}
              className={`border rounded-lg bg-white/3 p-4 flex flex-col gap-3 transition-colors ${
                dragTarget === persona.id ? "border-amber-400/60 bg-amber-900/10" : CATEGORY_COLOR[persona.category]
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragTarget(persona.id); }}
              onDragLeave={() => setDragTarget(null)}
              onDrop={(e) => handleDrop(e, persona.id)}
            >
              {/* Persona header */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-white">{persona.name}</h3>
                  <span className={`text-xs ${CATEGORY_COLOR[persona.category].split(" ")[0]}`}>
                    {CATEGORY_LABEL[persona.category]} · {persona.photos.length} photo{persona.photos.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <button
                  onClick={() => deletePersona(persona.id)}
                  className="text-gray-600 hover:text-red-400 text-xs transition-colors"
                >
                  Delete
                </button>
              </div>

              {/* Photo thumbnails */}
              {persona.photos.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                  {persona.photos.map((photo) => (
                    <div key={photo} className="relative group">
                      <div className="w-16 h-16 rounded bg-white/10 flex items-center justify-center overflow-hidden">
                        <span className="text-gray-500 text-xs text-center px-1">{photo.split(".")[0].slice(0, 10)}</span>
                      </div>
                      <button
                        onClick={() => deletePhoto(persona.id, photo)}
                        className="absolute -top-1 -right-1 w-4 h-4 bg-red-900 text-red-300 rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 mt-auto">
                <button
                  onClick={() => triggerUpload(persona.id)}
                  className="flex-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 text-gray-300 text-xs rounded transition-colors"
                >
                  + Upload Photo
                </button>
                <button
                  onClick={() => generateWithLikeness(persona)}
                  disabled={generating === persona.id || persona.photos.length === 0}
                  className="flex-1 px-3 py-1.5 bg-rose-900/40 hover:bg-rose-900/60 text-rose-200 text-xs rounded transition-colors disabled:opacity-40"
                >
                  {generating === persona.id ? "Generating..." : "Generate"}
                </button>
              </div>

              {/* Create queen button */}
              <button
                onClick={() => createQueenProfile(persona)}
                disabled={creatingQueen === persona.id}
                className="px-3 py-1.5 bg-amber-900/30 hover:bg-amber-900/50 text-amber-300 text-xs rounded transition-colors disabled:opacity-40 border border-amber-400/20"
              >
                {creatingQueen === persona.id ? "Generating queen profile..." : "Create Queen Profile"}
              </button>

              {/* Queen profile result */}
              {queenResult?.id === persona.id && (
                <div className="mt-1 rounded border border-amber-400/20 bg-amber-900/10 p-3">
                  <p className="text-xs font-medium text-amber-400">
                    {(queenResult.profile as { name?: string }).name} — {(queenResult.profile as { title?: string }).title}
                  </p>
                  <p className="mt-1 text-[10px] text-white/40">
                    Archetype: {(queenResult.profile as { archetype?: string }).archetype} · Queen profile saved to persona
                  </p>
                </div>
              )}

              {/* Result preview */}
              {generateTarget === persona.id && generateResult && (
                <div className="mt-2">
                  <img
                    src={generateResult}
                    alt="Generated"
                    className="w-full rounded border border-white/10"
                  />
                  <a
                    href={generateResult}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-gray-500 hover:text-gray-300 mt-1 block"
                  >
                    Open full size ↗
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />
    </div>
  );
}
