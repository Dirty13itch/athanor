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

Use cool graphite neutrals with faint blue bias.

| Token | Role | Target value |
| --- | --- | --- |
| `--bg-app` | overall page background | `oklch(0.14 0.008 252)` |
| `--bg-atmosphere` | atmospheric top-level glow carrier | `oklch(0.18 0.012 246 / 0.28)` |
| `--surface-rail` | sidebar / header / chrome rail | `oklch(0.17 0.01 248)` |
| `--surface-shell` | shell-adjacent elevated background | `oklch(0.19 0.012 246)` |
| `--surface-panel` | primary content panel | `oklch(0.205 0.012 248)` |
| `--surface-panel-2` | nested elevated panel | `oklch(0.235 0.014 246)` |
| `--surface-overlay` | drawers / dialogs / overlays | `oklch(0.24 0.016 244 / 0.94)` |
| `--surface-hero` | command-center spotlight panel | `oklch(0.23 0.026 232 / 0.94)` |
| `--surface-metric` | compact metric tile | `oklch(0.24 0.013 246 / 0.78)` |
| `--surface-instrument` | telemetry/chart well | `oklch(0.18 0.012 246 / 0.96)` |

### Borders and dividers

| Token | Role | Target value |
| --- | --- | --- |
| `--line-soft` | low-emphasis border | `oklch(0.42 0.014 246 / 0.64)` |
| `--line-strong` | strong border or separation | `oklch(0.58 0.024 232 / 0.82)` |
| `--line-focus` | focus-visible ring | `oklch(0.76 0.075 232 / 0.92)` |

### Text

| Token | Role | Target value |
| --- | --- | --- |
| `--text-primary` | primary body and heading text | `oklch(0.95 0.01 244)` |
| `--text-secondary` | secondary body and explanations | `oklch(0.83 0.012 244)` |
| `--text-muted` | labels, metadata, timestamps | `oklch(0.69 0.012 238)` |
| `--text-disabled` | disabled or inactive | `oklch(0.56 0.01 238)` |

## Structural accent

The structural accent is the system's main action color.

It should read as:

- ion blue
- precise
- operational

Not as:

- brand cobalt everywhere
- generic SaaS blue

| Token | Role | Target value |
| --- | --- | --- |
| `--accent-structural` | primary action / active selection / positive attention | `oklch(0.74 0.08 232)` |
| `--accent-structural-soft` | low-emphasis structural tint | `oklch(0.74 0.08 232 / 0.18)` |
| `--accent-structural-strong` | focused active edge light | `oklch(0.79 0.09 228)` |

## Severity signals

Severity colors are reserved for operational meaning only.

| Token | Role | Target value |
| --- | --- | --- |
| `--signal-success` | success / healthy | `oklch(0.76 0.14 158)` |
| `--signal-info` | passive info / progress / neutral action | `oklch(0.74 0.08 232)` |
| `--signal-warning` | warning / caution | `oklch(0.83 0.12 84)` |
| `--signal-danger` | error / incident / urgent failure | `oklch(0.68 0.18 24)` |
| `--signal-paused` | paused / held / draft / inert | `oklch(0.63 0.014 250)` |
| `--signal-review` | waiting for review / undefined | `oklch(0.72 0.09 302)` |

Rules:

- `warning` and `danger` are never used as domain branding
- `info` may align with the structural accent
- `paused` and `review` are secondary system states, not primary route accents

## Domain accents

Domain accents support categorization, not status.

Only use them where the category matters and the surface is not already dominated by severity.

| Token | Domain | Target value |
| --- | --- | --- |
| `--domain-core` | command / system / governor | `oklch(0.74 0.08 232)` |
| `--domain-workforce` | tasks / agents / queue | `oklch(0.76 0.08 196)` |
| `--domain-intelligence` | review / learning / model governance | `oklch(0.74 0.09 294)` |
| `--domain-memory` | personal data / knowledge / retention | `oklch(0.74 0.09 170)` |
| `--domain-monitoring` | services / gpu / monitoring | `oklch(0.77 0.07 205)` |
| `--domain-media` | media / gallery / creative | `oklch(0.76 0.11 332)` |
| `--domain-home` | home / device orchestration | `oklch(0.78 0.10 148)` |

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

- `--chart-cat-1`: `oklch(0.74 0.08 232)`
- `--chart-cat-2`: `oklch(0.77 0.08 205)`
- `--chart-cat-3`: `oklch(0.74 0.09 170)`
- `--chart-cat-4`: `oklch(0.72 0.09 294)`
- `--chart-cat-5`: `oklch(0.75 0.10 332)`
- `--chart-cat-6`: `oklch(0.76 0.12 158)`
- `--chart-cat-7`: `oklch(0.8 0.12 64)`
- `--chart-cat-8`: `oklch(0.66 0.016 248)`

### Sequential scales

- Primary sequential: blue-cyan
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
| `--state-hover` | hover tint on neutral surfaces | `oklch(0.31 0.016 244 / 0.72)` |
| `--state-pressed` | pressed tint | `oklch(0.34 0.018 244 / 0.82)` |
| `--state-selected` | selected background | `oklch(0.74 0.08 232 / 0.18)` |
| `--state-focus-ring` | keyboard focus ring | `oklch(0.79 0.09 228 / 0.92)` |

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

- Use cool edge lighting for focus and selected states
- Use domain edge lighting sparingly on hero or spotlight surfaces
- Do not use warm glows as the base identity

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
