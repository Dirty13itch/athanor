"use client";

import { useState } from "react";
import type {
  Inspection,
  BuildingEnvelope,
  BlowerDoorTest,
  DuctLeakageTest,
  InsulationEntry,
  WindowEntry,
  HvacSystem,
  FoundationType,
  InsulationType,
  WindowFrameType,
  HvacSystemType,
  DuctTestMethod,
} from "@/types/inspection";

// ── Shared ─────────────────────────────────────────────────────────────

interface SectionProps {
  inspection: Inspection;
  onSave: (data: Partial<Inspection>) => Promise<void>;
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-muted-foreground">
        {label}
      </label>
      {children}
    </div>
  );
}

const input =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const select =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function SectionWrapper({
  title,
  isEditing,
  onEdit,
  onCancel,
  onSave,
  saving,
  children,
}: {
  title: string;
  isEditing: boolean;
  onEdit: () => void;
  onCancel: () => void;
  onSave: () => void;
  saving: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </h3>
        {isEditing ? (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="rounded px-3 py-1 text-xs text-muted-foreground hover:bg-accent"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onSave}
              disabled={saving}
              className="rounded bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={onEdit}
            className="rounded px-3 py-1 text-xs text-primary hover:bg-primary/10"
          >
            Edit
          </button>
        )}
      </div>
      <div className="mt-3">{children}</div>
    </section>
  );
}

// ── Building Envelope ──────────────────────────────────────────────────

export function BuildingEnvelopeSection({ inspection, onSave }: SectionProps) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const existing = inspection.buildingEnvelope;
  const [form, setForm] = useState<BuildingEnvelope>(
    existing ?? {
      orientation: "",
      sqft: 0,
      ceilingHeight: 9,
      stories: 1,
      foundationType: "slab",
    },
  );

  async function save() {
    setSaving(true);
    await onSave({ buildingEnvelope: form });
    setSaving(false);
    setEditing(false);
  }

  if (!editing) {
    return (
      <SectionWrapper
        title="Building Envelope"
        isEditing={false}
        onEdit={() => setEditing(true)}
        onCancel={() => setEditing(false)}
        onSave={save}
        saving={saving}
      >
        {existing ? (
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted-foreground">Orientation</dt>
            <dd>{existing.orientation || "—"}</dd>
            <dt className="text-muted-foreground">Sq Ft</dt>
            <dd>{existing.sqft.toLocaleString()}</dd>
            <dt className="text-muted-foreground">Ceiling Height</dt>
            <dd>{existing.ceilingHeight} ft</dd>
            <dt className="text-muted-foreground">Stories</dt>
            <dd>{existing.stories}</dd>
            <dt className="text-muted-foreground">Foundation</dt>
            <dd>{existing.foundationType.replace("_", " ")}</dd>
          </dl>
        ) : (
          <p className="text-sm text-muted-foreground">Not recorded yet.</p>
        )}
      </SectionWrapper>
    );
  }

  return (
    <SectionWrapper
      title="Building Envelope"
      isEditing
      onEdit={() => setEditing(true)}
      onCancel={() => setEditing(false)}
      onSave={() => void save()}
      saving={saving}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Orientation">
          <input
            className={input}
            value={form.orientation}
            onChange={(e) => setForm({ ...form, orientation: e.target.value })}
            placeholder="N, S, E, W"
          />
        </Field>
        <Field label="Square Footage">
          <input
            className={input}
            type="number"
            value={form.sqft || ""}
            onChange={(e) =>
              setForm({ ...form, sqft: parseInt(e.target.value) || 0 })
            }
          />
        </Field>
        <Field label="Ceiling Height (ft)">
          <input
            className={input}
            type="number"
            step="0.5"
            value={form.ceilingHeight || ""}
            onChange={(e) =>
              setForm({
                ...form,
                ceilingHeight: parseFloat(e.target.value) || 9,
              })
            }
          />
        </Field>
        <Field label="Stories">
          <input
            className={input}
            type="number"
            min="1"
            max="4"
            value={form.stories || ""}
            onChange={(e) =>
              setForm({ ...form, stories: parseInt(e.target.value) || 1 })
            }
          />
        </Field>
        <Field label="Foundation Type">
          <select
            className={select}
            value={form.foundationType}
            onChange={(e) =>
              setForm({
                ...form,
                foundationType: e.target.value as FoundationType,
              })
            }
          >
            <option value="slab">Slab</option>
            <option value="crawlspace">Crawlspace</option>
            <option value="basement">Basement</option>
            <option value="pier_beam">Pier & Beam</option>
          </select>
        </Field>
      </div>
    </SectionWrapper>
  );
}

// ── Blower Door ────────────────────────────────────────────────────────

export function BlowerDoorSection({ inspection, onSave }: SectionProps) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const existing = inspection.blowerDoor;
  const [form, setForm] = useState<BlowerDoorTest>(
    existing ?? { cfm50: 0, ach50: 0, enclosureArea: 0, passFail: false },
  );

  async function save() {
    setSaving(true);
    await onSave({ blowerDoor: form });
    setSaving(false);
    setEditing(false);
  }

  if (!editing) {
    return (
      <SectionWrapper
        title="Blower Door Test"
        isEditing={false}
        onEdit={() => setEditing(true)}
        onCancel={() => setEditing(false)}
        onSave={save}
        saving={saving}
      >
        {existing ? (
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted-foreground">CFM50</dt>
            <dd>{existing.cfm50}</dd>
            <dt className="text-muted-foreground">ACH50</dt>
            <dd>{existing.ach50}</dd>
            <dt className="text-muted-foreground">Enclosure Area</dt>
            <dd>{existing.enclosureArea} sq ft</dd>
            <dt className="text-muted-foreground">Pass/Fail</dt>
            <dd>{existing.passFail ? "Pass" : "Fail"}</dd>
          </dl>
        ) : (
          <p className="text-sm text-muted-foreground">Not recorded yet.</p>
        )}
      </SectionWrapper>
    );
  }

  return (
    <SectionWrapper
      title="Blower Door Test"
      isEditing
      onEdit={() => setEditing(true)}
      onCancel={() => setEditing(false)}
      onSave={() => void save()}
      saving={saving}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="CFM50">
          <input
            className={input}
            type="number"
            value={form.cfm50 || ""}
            onChange={(e) =>
              setForm({ ...form, cfm50: parseInt(e.target.value) || 0 })
            }
          />
        </Field>
        <Field label="ACH50">
          <input
            className={input}
            type="number"
            step="0.1"
            value={form.ach50 || ""}
            onChange={(e) =>
              setForm({ ...form, ach50: parseFloat(e.target.value) || 0 })
            }
          />
        </Field>
        <Field label="Enclosure Area (sq ft)">
          <input
            className={input}
            type="number"
            value={form.enclosureArea || ""}
            onChange={(e) =>
              setForm({
                ...form,
                enclosureArea: parseInt(e.target.value) || 0,
              })
            }
          />
        </Field>
        <Field label="Pass/Fail">
          <select
            className={select}
            value={form.passFail ? "pass" : "fail"}
            onChange={(e) =>
              setForm({ ...form, passFail: e.target.value === "pass" })
            }
          >
            <option value="pass">Pass</option>
            <option value="fail">Fail</option>
          </select>
        </Field>
      </div>
    </SectionWrapper>
  );
}

// ── Duct Leakage ───────────────────────────────────────────────────────

export function DuctLeakageSection({ inspection, onSave }: SectionProps) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const existing = inspection.ductLeakage;
  const [form, setForm] = useState<DuctLeakageTest>(
    existing ?? {
      cfm25Total: 0,
      cfm25Outside: 0,
      testMethod: "total_leakage",
    },
  );

  async function save() {
    setSaving(true);
    await onSave({ ductLeakage: form });
    setSaving(false);
    setEditing(false);
  }

  if (!editing) {
    return (
      <SectionWrapper
        title="Duct Leakage Test"
        isEditing={false}
        onEdit={() => setEditing(true)}
        onCancel={() => setEditing(false)}
        onSave={save}
        saving={saving}
      >
        {existing ? (
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted-foreground">CFM25 Total</dt>
            <dd>{existing.cfm25Total}</dd>
            <dt className="text-muted-foreground">CFM25 Outside</dt>
            <dd>{existing.cfm25Outside}</dd>
            <dt className="text-muted-foreground">Test Method</dt>
            <dd>{existing.testMethod.replace(/_/g, " ")}</dd>
          </dl>
        ) : (
          <p className="text-sm text-muted-foreground">Not recorded yet.</p>
        )}
      </SectionWrapper>
    );
  }

  return (
    <SectionWrapper
      title="Duct Leakage Test"
      isEditing
      onEdit={() => setEditing(true)}
      onCancel={() => setEditing(false)}
      onSave={() => void save()}
      saving={saving}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="CFM25 Total">
          <input
            className={input}
            type="number"
            value={form.cfm25Total || ""}
            onChange={(e) =>
              setForm({ ...form, cfm25Total: parseInt(e.target.value) || 0 })
            }
          />
        </Field>
        <Field label="CFM25 Outside">
          <input
            className={input}
            type="number"
            value={form.cfm25Outside || ""}
            onChange={(e) =>
              setForm({ ...form, cfm25Outside: parseInt(e.target.value) || 0 })
            }
          />
        </Field>
        <Field label="Test Method">
          <select
            className={select}
            value={form.testMethod}
            onChange={(e) =>
              setForm({ ...form, testMethod: e.target.value as DuctTestMethod })
            }
          >
            <option value="total_leakage">Total Leakage</option>
            <option value="leakage_to_outside">Leakage to Outside</option>
            <option value="both">Both</option>
          </select>
        </Field>
      </div>
    </SectionWrapper>
  );
}

// ── Insulation ─────────────────────────────────────────────────────────

export function InsulationSection({ inspection, onSave }: SectionProps) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [entries, setEntries] = useState<InsulationEntry[]>(
    inspection.insulation ?? [],
  );

  function addEntry() {
    setEntries([
      ...entries,
      {
        id: crypto.randomUUID(),
        location: "",
        rValue: 0,
        type: "fiberglass_batt",
        depth: 0,
      },
    ]);
  }

  function removeEntry(id: string) {
    setEntries(entries.filter((e) => e.id !== id));
  }

  function updateEntry(id: string, updates: Partial<InsulationEntry>) {
    setEntries(entries.map((e) => (e.id === id ? { ...e, ...updates } : e)));
  }

  async function save() {
    setSaving(true);
    await onSave({ insulation: entries });
    setSaving(false);
    setEditing(false);
  }

  if (!editing) {
    return (
      <SectionWrapper
        title={`Insulation (${entries.length})`}
        isEditing={false}
        onEdit={() => setEditing(true)}
        onCancel={() => setEditing(false)}
        onSave={save}
        saving={saving}
      >
        {entries.length > 0 ? (
          <div className="space-y-2 text-sm">
            {entries.map((e) => (
              <div
                key={e.id}
                className="flex justify-between rounded border border-border px-3 py-2"
              >
                <span>
                  {e.location || "—"} · R-{e.rValue}
                </span>
                <span className="text-muted-foreground">
                  {e.type.replace(/_/g, " ")} · {e.depth}&quot;
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No entries yet.</p>
        )}
      </SectionWrapper>
    );
  }

  return (
    <SectionWrapper
      title={`Insulation (${entries.length})`}
      isEditing
      onEdit={() => setEditing(true)}
      onCancel={() => {
        setEntries(inspection.insulation ?? []);
        setEditing(false);
      }}
      onSave={() => void save()}
      saving={saving}
    >
      <div className="space-y-3">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className="grid gap-2 rounded border border-border p-3 sm:grid-cols-5"
          >
            <input
              className={input}
              placeholder="Location"
              value={entry.location}
              onChange={(e) =>
                updateEntry(entry.id, { location: e.target.value })
              }
            />
            <input
              className={input}
              type="number"
              placeholder="R-Value"
              value={entry.rValue || ""}
              onChange={(e) =>
                updateEntry(entry.id, {
                  rValue: parseInt(e.target.value) || 0,
                })
              }
            />
            <select
              className={select}
              value={entry.type}
              onChange={(e) =>
                updateEntry(entry.id, {
                  type: e.target.value as InsulationType,
                })
              }
            >
              <option value="fiberglass_batt">Fiberglass Batt</option>
              <option value="blown_cellulose">Blown Cellulose</option>
              <option value="blown_fiberglass">Blown Fiberglass</option>
              <option value="spray_foam_open">Open Cell Spray Foam</option>
              <option value="spray_foam_closed">Closed Cell Spray Foam</option>
              <option value="rigid_foam">Rigid Foam</option>
              <option value="mineral_wool">Mineral Wool</option>
            </select>
            <input
              className={input}
              type="number"
              step="0.5"
              placeholder='Depth (")'
              value={entry.depth || ""}
              onChange={(e) =>
                updateEntry(entry.id, {
                  depth: parseFloat(e.target.value) || 0,
                })
              }
            />
            <button
              type="button"
              onClick={() => removeEntry(entry.id)}
              className="rounded px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={addEntry}
          className="w-full rounded-md border border-dashed border-border py-2 text-sm text-muted-foreground hover:bg-accent"
        >
          + Add Insulation Entry
        </button>
      </div>
    </SectionWrapper>
  );
}

// ── Windows ────────────────────────────────────────────────────────────

export function WindowsSection({ inspection, onSave }: SectionProps) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [entries, setEntries] = useState<WindowEntry[]>(
    inspection.windows ?? [],
  );

  function addEntry() {
    setEntries([
      ...entries,
      {
        id: crypto.randomUUID(),
        location: "",
        uFactor: 0.3,
        shgc: 0.25,
        frameType: "vinyl",
        count: 1,
        area: 0,
      },
    ]);
  }

  function removeEntry(id: string) {
    setEntries(entries.filter((e) => e.id !== id));
  }

  function updateEntry(id: string, updates: Partial<WindowEntry>) {
    setEntries(entries.map((e) => (e.id === id ? { ...e, ...updates } : e)));
  }

  async function save() {
    setSaving(true);
    await onSave({ windows: entries });
    setSaving(false);
    setEditing(false);
  }

  if (!editing) {
    return (
      <SectionWrapper
        title={`Windows (${entries.length})`}
        isEditing={false}
        onEdit={() => setEditing(true)}
        onCancel={() => setEditing(false)}
        onSave={save}
        saving={saving}
      >
        {entries.length > 0 ? (
          <div className="space-y-2 text-sm">
            {entries.map((e) => (
              <div
                key={e.id}
                className="flex justify-between rounded border border-border px-3 py-2"
              >
                <span>
                  {e.location || "—"} · U-{e.uFactor} · SHGC {e.shgc}
                </span>
                <span className="text-muted-foreground">
                  {e.frameType} · {e.count}x · {e.area} sq ft
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No entries yet.</p>
        )}
      </SectionWrapper>
    );
  }

  return (
    <SectionWrapper
      title={`Windows (${entries.length})`}
      isEditing
      onEdit={() => setEditing(true)}
      onCancel={() => {
        setEntries(inspection.windows ?? []);
        setEditing(false);
      }}
      onSave={() => void save()}
      saving={saving}
    >
      <div className="space-y-3">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className="grid gap-2 rounded border border-border p-3 sm:grid-cols-3"
          >
            <input
              className={input}
              placeholder="Location"
              value={entry.location}
              onChange={(e) =>
                updateEntry(entry.id, { location: e.target.value })
              }
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                className={input}
                type="number"
                step="0.01"
                placeholder="U-Factor"
                value={entry.uFactor || ""}
                onChange={(e) =>
                  updateEntry(entry.id, {
                    uFactor: parseFloat(e.target.value) || 0,
                  })
                }
              />
              <input
                className={input}
                type="number"
                step="0.01"
                placeholder="SHGC"
                value={entry.shgc || ""}
                onChange={(e) =>
                  updateEntry(entry.id, {
                    shgc: parseFloat(e.target.value) || 0,
                  })
                }
              />
            </div>
            <div className="flex gap-2">
              <select
                className={select}
                value={entry.frameType}
                onChange={(e) =>
                  updateEntry(entry.id, {
                    frameType: e.target.value as WindowFrameType,
                  })
                }
              >
                <option value="vinyl">Vinyl</option>
                <option value="wood">Wood</option>
                <option value="aluminum">Aluminum</option>
                <option value="fiberglass">Fiberglass</option>
                <option value="composite">Composite</option>
              </select>
              <input
                className={input}
                type="number"
                min="1"
                placeholder="Count"
                value={entry.count || ""}
                onChange={(e) =>
                  updateEntry(entry.id, {
                    count: parseInt(e.target.value) || 1,
                  })
                }
              />
              <button
                type="button"
                onClick={() => removeEntry(entry.id)}
                className="rounded px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
              >
                X
              </button>
            </div>
          </div>
        ))}
        <button
          type="button"
          onClick={addEntry}
          className="w-full rounded-md border border-dashed border-border py-2 text-sm text-muted-foreground hover:bg-accent"
        >
          + Add Window Entry
        </button>
      </div>
    </SectionWrapper>
  );
}

// ── HVAC Systems ───────────────────────────────────────────────────────

export function HvacSection({ inspection, onSave }: SectionProps) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [entries, setEntries] = useState<HvacSystem[]>(
    inspection.hvacSystems ?? [],
  );

  function addEntry() {
    setEntries([
      ...entries,
      {
        id: crypto.randomUUID(),
        systemType: "furnace",
        model: "",
        capacity: "",
        efficiencyRating: "",
        ductLocation: "",
      },
    ]);
  }

  function removeEntry(id: string) {
    setEntries(entries.filter((e) => e.id !== id));
  }

  function updateEntry(id: string, updates: Partial<HvacSystem>) {
    setEntries(entries.map((e) => (e.id === id ? { ...e, ...updates } : e)));
  }

  async function save() {
    setSaving(true);
    await onSave({ hvacSystems: entries });
    setSaving(false);
    setEditing(false);
  }

  if (!editing) {
    return (
      <SectionWrapper
        title={`HVAC Systems (${entries.length})`}
        isEditing={false}
        onEdit={() => setEditing(true)}
        onCancel={() => setEditing(false)}
        onSave={save}
        saving={saving}
      >
        {entries.length > 0 ? (
          <div className="space-y-2 text-sm">
            {entries.map((e) => (
              <div
                key={e.id}
                className="flex justify-between rounded border border-border px-3 py-2"
              >
                <span>
                  {e.systemType.replace(/_/g, " ")} · {e.model || "—"}
                </span>
                <span className="text-muted-foreground">
                  {e.capacity} · {e.efficiencyRating}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No entries yet.</p>
        )}
      </SectionWrapper>
    );
  }

  return (
    <SectionWrapper
      title={`HVAC Systems (${entries.length})`}
      isEditing
      onEdit={() => setEditing(true)}
      onCancel={() => {
        setEntries(inspection.hvacSystems ?? []);
        setEditing(false);
      }}
      onSave={() => void save()}
      saving={saving}
    >
      <div className="space-y-3">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className="grid gap-2 rounded border border-border p-3 sm:grid-cols-3"
          >
            <select
              className={select}
              value={entry.systemType}
              onChange={(e) =>
                updateEntry(entry.id, {
                  systemType: e.target.value as HvacSystemType,
                })
              }
            >
              <option value="furnace">Furnace</option>
              <option value="ac">Air Conditioner</option>
              <option value="heat_pump">Heat Pump</option>
              <option value="boiler">Boiler</option>
              <option value="mini_split">Mini Split</option>
              <option value="geothermal">Geothermal</option>
            </select>
            <input
              className={input}
              placeholder="Model"
              value={entry.model}
              onChange={(e) =>
                updateEntry(entry.id, { model: e.target.value })
              }
            />
            <input
              className={input}
              placeholder="Capacity (BTU/tons)"
              value={entry.capacity}
              onChange={(e) =>
                updateEntry(entry.id, { capacity: e.target.value })
              }
            />
            <input
              className={input}
              placeholder="Efficiency (SEER/AFUE)"
              value={entry.efficiencyRating}
              onChange={(e) =>
                updateEntry(entry.id, { efficiencyRating: e.target.value })
              }
            />
            <input
              className={input}
              placeholder="Duct Location"
              value={entry.ductLocation}
              onChange={(e) =>
                updateEntry(entry.id, { ductLocation: e.target.value })
              }
            />
            <button
              type="button"
              onClick={() => removeEntry(entry.id)}
              className="rounded px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={addEntry}
          className="w-full rounded-md border border-dashed border-border py-2 text-sm text-muted-foreground hover:bg-accent"
        >
          + Add HVAC System
        </button>
      </div>
    </SectionWrapper>
  );
}
