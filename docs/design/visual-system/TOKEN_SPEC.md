# Token Specification

## Purpose

This is the canonical semantic token specification for the Athanor redesign.

These tokens are design decisions, not implementation guesses.

## Token strategy

The system uses four independent token layers:

1. structure
2. severity
3. domain
4. interaction

Each visual decision must declare which layer it belongs to.

## Naming rules

- Token names describe role, not pigment.
- Avoid names like `amber`, `warmth`, `ember`, or `furnace`.
- Prefer names like `surface-rail`, `signal-warning`, `chart-category-3`, `accent-domain-intelligence`.

## Core neutral system

### Background and shell

Use neutral charcoal and industrial gray neutrals with no page-level color wash.

| Token | Role | Target value |
| --- | --- | --- |
| `--bg-app` | overall page background | `#161616` |
| `--bg-atmosphere` | neutral atmospheric top-level glow carrier | `rgb(255 255 255 / 0.03)` |
| `--surface-rail` | sidebar / header / chrome rail | `#1a1a1a` |
| `--surface-shell` | shell-adjacent elevated background | `#1f1f1f` |
| `--surface-panel` | primary content panel | `#262626` |
| `--surface-panel-2` | nested elevated panel | `#2d2d2d` |
| `--surface-overlay` | drawers / dialogs / overlays | `rgb(38 38 38 / 0.94)` |
| `--surface-hero` | command-center spotlight panel | `#212121` |
| `--surface-metric` | compact metric tile | `rgb(42 42 42 / 0.86)` |
| `--surface-instrument` | telemetry/chart well | `#1f1f1f` |

### Borders and dividers

| Token | Role | Target value |
| --- | --- | --- |
| `--line-soft` | low-emphasis border | `rgb(244 244 244 / 0.1)` |
| `--line-strong` | strong border or separation | `#525252` |
| `--line-focus` | focus-visible ring | `#78a9ff` |

### Text

| Token | Role | Target value |
| --- | --- | --- |
| `--text-primary` | primary body and heading text | `#f4f4f4` |
| `--text-secondary` | secondary body and explanations | `#dde1e6` |
| `--text-muted` | labels, metadata, timestamps | `#a8a8a8` |
| `--text-disabled` | disabled or inactive | `#6f6f6f` |

## Structural accent

The structural accent is the system's main action color.

It should read as:

- bright industrial blue
- precise
- operational

Not as:

- page-wide blue atmosphere
- generic SaaS blue branding everywhere

| Token | Role | Target value |
| --- | --- | --- |
| `--accent-structural` | primary action / active selection / positive attention | `#78a9ff` |
| `--accent-structural-soft` | low-emphasis structural tint | `rgb(120 169 255 / 0.16)` |
| `--accent-structural-strong` | focused active edge light | `#a6c8ff` |

## Severity signals

Severity colors are reserved for operational meaning only.

| Token | Role | Target value |
| --- | --- | --- |
| `--signal-success` | success / healthy | `#42be65` |
| `--signal-info` | passive info / progress / neutral action | `#78a9ff` |
| `--signal-warning` | warning / caution | `#f1c21b` |
| `--signal-danger` | error / incident / urgent failure | `#fa4d56` |
| `--signal-paused` | paused / held / draft / inert | `#8d8d8d` |
| `--signal-review` | waiting for review / undefined | `#be95ff` |

Rules:

- `warning` and `danger` are never used as domain branding
- `info` may align with the structural accent
- `paused` and `review` are secondary system states, not primary route accents

## Domain accents

Domain accents support categorization, not status.

Only use them where the category matters and the surface is not already dominated by severity.

| Token | Domain | Target value |
| --- | --- | --- |
| `--domain-core` | command / system / governor | `#78a9ff` |
| `--domain-workforce` | tasks / agents / queue | `#3ddbd9` |
| `--domain-intelligence` | review / learning / model governance | `#be95ff` |
| `--domain-memory` | personal data / knowledge / retention | `#42be65` |
| `--domain-monitoring` | services / gpu / monitoring | `#33b1ff` |
| `--domain-media` | media / gallery / creative | `#ff7eb6` |
| `--domain-home` | home / device orchestration | `#82cfff` |

Rules:

- Domain accents appear as trims, chart highlights, section markers, tabs, or small supporting glows.
- Domain accents should not recolor entire route backgrounds.
- Domain accents must yield to severity colors when the surface represents a problem.

## Chart grammar

### Categorical order

Use one fixed order for categorical charts:

1. blue
2. cyan
3. teal
4. violet
5. magenta
6. green
7. orange
8. gray

Target tokens:

- `--chart-cat-1`: `#78a9ff`
- `--chart-cat-2`: `#33b1ff`
- `--chart-cat-3`: `#42be65`
- `--chart-cat-4`: `#be95ff`
- `--chart-cat-5`: `#ff7eb6`
- `--chart-cat-6`: `#3ddbd9`
- `--chart-cat-7`: `#f1c21b`
- `--chart-cat-8`: `#8d8d8d`

### Sequential scales

- Primary sequential: blue
- Secondary sequential: teal
- Review/intelligence sequential: violet

### Alert palette

Use only for status-bearing visualizations:

- danger
- warning
- success
- info

### Chart rules

- Prefer direct labels over legends when space allows.
- Use legends only when multiple categories must be decoded.
- Never use gradient as a substitute for ordered quantitative scale without explicit purpose.
- Never use category colors to imply severity.

## Interaction tokens

| Token | Role | Target value |
| --- | --- | --- |
| `--state-hover` | hover tint on neutral surfaces | `rgb(255 255 255 / 0.05)` |
| `--state-pressed` | pressed tint | `rgb(255 255 255 / 0.08)` |
| `--state-selected` | selected background | `rgb(120 169 255 / 0.14)` |
| `--state-focus-ring` | keyboard focus ring | `rgb(166 200 255 / 0.92)` |

## Material behavior

### Matte vs gloss

Athanor should be primarily matte.

Allowed:

- restrained internal highlight
- soft edge light
- subtle glassiness on overlays only

Avoid:

- glossy plastic surfaces
- mirror-like reflections
- bright internal glows across normal panels

### Edge-light rules

- Use bright blue edge lighting for focus and selected states
- Use domain edge lighting sparingly on hero or spotlight surfaces
- Do not use warm glows or page-level colored fog as the base identity

## Typography specification

### Final stack

- Heading/display family: `Space Grotesk`
- System/body family: `IBM Plex Sans`
- Mono/data family: `IBM Plex Mono`

### Role rules

- Display/headline: short, high-importance, route headers, hero metrics
- Title: section grouping and panel titles
- Body: explanations, annotations, normal operator prose
- Label: metadata, chips, tiny headers, chart and control labels
- Mono: metrics, IDs, timestamps, commands, counts requiring numeric stability

### Why Cormorant does not survive

Cormorant carries an editorial and atmospheric tone.

That tone conflicts with:

- precision
- trust
- technical density
- control-room clarity

## Motion tokens

### Duration

- fast: `120ms`
- standard: `180ms`
- slow: `260ms`
- emphasis: `340ms`

### Motion classes

- productive: default transitions, list updates, drawers, tabs
- expressive: command-center spotlight moments, escalations, major successful transitions

### Rules

- expressive motion is rare
- productive motion is default
- respect `prefers-reduced-motion`

## Token migration note

When implementation starts, legacy token names should be retired or aliased away from:

- `--amber`
- `--glow-warm`
- `--system-warmth`
- `--furnace-glow`

Replacement naming should reflect role and metaphor-neutral semantics.
