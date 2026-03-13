# Visual Audit

## Audit scope

This audit covers the live shell and active operator routes documented in:

- `docs/atlas/UI_ATLAS.md`
- `docs/atlas/inventory/ui-inventory.json`

And the current screenshot evidence under:

- `projects/dashboard/tests/e2e/visual.spec.ts-snapshots`

## Audit method

Current-state review used four evidence layers:

1. live theme tokens and surface utilities in `src/app/globals.css`
2. active shell and command-center source
3. route inventory from the atlas
4. Playwright baseline screenshots for desktop and mobile

## Executive finding

The dashboard is structurally strong and visually transitional.

What is already good:

- shell structure and navigation hierarchy
- route grouping and information architecture
- operator density
- basic dark-theme discipline
- stronger panel depth than the earlier flat amber-on-black baseline

What is still unresolved:

- legacy furnace-era semantics and variable naming
- incomplete signal governance
- incomplete material hierarchy
- inconsistent accent strategy across routes
- chart grammar not yet locked
- typography still split between technical UI needs and older editorial heading tone

## Current-state strengths

### Shell

- The shell already reads as an operator console rather than a generic web app.
- Sidebar, header, command palette, and quick actions are well structured.
- Surface separation between shell and content is working.

### Command Center

- The route has strong information hierarchy.
- The route already feels like the main command surface.
- Core system cards, unified stream, system map, governance cards, and cluster posture are composed well.

### Route family structure

- The active route families are coherent.
- The current 25-route shell is sufficient and worth preserving.
- Shared console families are already a strong abstraction.

### Darkness and depth

- The dashboard no longer feels purely flat.
- The graphite-and-steel correction improved readability and maturity.

## Current-state weaknesses

### 1. Mixed metaphor

The repo still contains old metaphor language and semantics:

- `--system-warmth`
- `--furnace-glow`
- `--glow-warm`
- "The Furnace" in command-center docs

Even when the palette is cooler, these names keep the design language mentally anchored to the wrong metaphor.

### 2. Color system is still transitional

The current tokens improved the palette, but the system still mixes:

- a structural blue primary
- warning amber
- leftover warm-named variables
- route-level custom hues
- chart colors that are not yet governed as one formal grammar

### 3. Material hierarchy is under-specified

The current surface classes are a strong start, but too many surfaces still feel like variations of the same card treatment.

The system needs a clearer distinction between:

- shell chrome
- workspace panels
- metric tiles
- branded/hero surfaces
- overlays and drawers
- dense tables and telemetry wells

### 4. Typography voice is split

The current typography still carries the older Cormorant-based heading tone from a more literary or atmospheric direction.

That conflicts with the new operator identity.

### 5. Multi-signal behavior is not yet governed

There is not yet one documented answer for:

- which colors mean status
- which colors mean domain
- which colors mean emphasis
- when multiple accents may coexist

### 6. Charts are improved but not fully standardized

The chart palette is better than before, but not yet formalized as:

- sequential rule set
- categorical rule set
- alert palette
- threshold palette
- legend and labeling rules

### 7. Motion is not yet a designed system

Reduced-motion support exists, which is good.

What is missing is a full motion grammar for:

- productive motion
- expressive motion
- escalation motion
- ambient motion

## Surface-by-surface audit

### App shell

What works:

- sidebar and top bar separation
- quick-access link treatment
- compact operator framing

What feels inconsistent:

- active-nav emphasis is still too tied to the primary accent rather than a broader signal/material system
- the shell brand block still carries old emotional tone in copy

Decision:

- preserve shell structure
- redesign shell materials, typography, and signal treatment

### Command Center

What works:

- strong composition
- correct route priority
- useful card families

What feels inconsistent:

- cards are all aesthetically close cousins
- the route wants a richer notion of priority, spotlight, and instrument zones

Decision:

- preserve layout
- redesign card hierarchy, hero/spotlight behavior, and chart grammar

### Agents

What works:

- dense operational posture
- agent detail and roster surfaces fit the product

What feels inconsistent:

- the route needs stronger visual distinction between:
  - roster
  - current work
  - lineage
  - provider posture
  - judge posture

Decision:

- redesign agent visual strata, not the IA

### Tasks / Workplanner / Notifications

What works:

- operational density
- strong path to action

What feels inconsistent:

- severity, queue state, approval state, and provider state are not yet visually separated by a single grammar

Decision:

- formalize severity vs domain vs emphasis rules

### Monitoring / GPU / Services

What works:

- dense console character
- strong use of metrics

What feels inconsistent:

- the routes are closest to a real control-room tone, but their charts and status cues need a stricter instrumentation grammar

Decision:

- use these as primary reference routes for the final metric/telemetry language

### Chat / Learning / Review / Personal Data

What works:

- strong route roles

What feels inconsistent:

- some routes still inherit visual decisions from generic card/dashboard language instead of a clear route-specific operator mode

Decision:

- preserve route structure
- retune route-level emphasis and domain accent behavior

## Category audit

### Charts and graph colors

Findings:

- current charts are better than before
- there is still no formal categorical/sequential/alert split
- some chart colors are still too close in value on dark surfaces

Decision:

- create one canonical chart grammar

### Badges and status dots

Findings:

- warning uses amber correctly in some places
- status semantics are not yet fully separated from domain accents

Decision:

- keep severity semantics strict
- do not let domain accents imitate severity colors

### Cards and panel tiers

Findings:

- improved surfaces exist
- not enough distinction yet between shell, telemetry, hero, overlay, and dense utility surfaces

Decision:

- expand the material system

### Navigation / sidebar / top bar

Findings:

- very strong layout
- visually good enough to preserve
- still needs typographic and material unification

Decision:

- retune, not redesign

### Dialogs and drawers

Findings:

- structurally fine
- visually inherit generic panel behavior

Decision:

- bring them under explicit overlay rules

### Agent portraits and activity surfaces

Findings:

- the existing route role is solid
- the surfaces need more character and status clarity

Decision:

- redesign within the existing structure

### Typography roles

Findings:

- current headline/body split is not final
- the old heading voice is too atmospheric for the new identity

Decision:

- replace headline tone with a more technical voice

### Spacing and density rhythm

Findings:

- current density is strong
- rhythm is mostly good
- some surfaces need a clearer tiering between compact data and operator explanation

Decision:

- formalize spacing/elevation pairings by component type

### Motion and ambience

Findings:

- motion is present but not yet designed as a system
- ambient semantics still inherit old warmth/furnace naming

Decision:

- rebuild motion language around productive control-room motion

## Audit conclusion

Do not rebuild the dashboard structure.

Do:

- replace the visual metaphor
- define a full token and signal system
- redesign materials, typography, charts, and motion together
- apply the redesign route by route after the system contract is locked
