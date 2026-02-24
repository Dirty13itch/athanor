# Athanor Design System

Dark, minimal, warm. Inspired by the Twelve Words — Cormorant Garamond, subtle warmth, no clutter. This is a crafted interface, not a generic admin panel.

---

## Principles

1. **Dark-first** — Deep black backgrounds (7% lightness), never gray. Light mode exists in CSS for completeness but is unused.
2. **Warm amber accent** — Primary color is warm amber/gold (oklch 0.75 0.08 65). Not neon, not cool. Everything warm.
3. **Dense data, sparse chrome** — Maximize information density. Minimize decorative elements. Every pixel earns its place.
4. **Serif for identity, sans for interface** — Cormorant Garamond for headings (h1-h4, brand text). Inter for everything else. Geist Mono for data/metrics.
5. **Subtle borders** — 6% white opacity borders. Almost invisible. Enough to separate, not enough to distract.

---

## Color Palette

All colors in OKLCh for perceptual uniformity.

### Core

| Token | Value | Usage |
|-------|-------|-------|
| `--background` | `oklch(0.07 0 0)` | Page background — near-black |
| `--foreground` | `oklch(0.93 0.005 60)` | Primary text — warm off-white |
| `--card` | `oklch(0.12 0.003 60)` | Card surfaces — slightly elevated |
| `--primary` | `oklch(0.75 0.08 65)` | Amber accent — buttons, links, focus |
| `--primary-foreground` | `oklch(0.07 0 0)` | Text on primary — black |
| `--muted` | `oklch(0.18 0.005 60)` | Muted surfaces — disabled, inactive |
| `--muted-foreground` | `oklch(0.55 0.01 60)` | Secondary text — labels, captions |

### Semantic

| Token | Value | Usage |
|-------|-------|-------|
| `--destructive` | `oklch(0.65 0.2 25)` | Errors, danger, delete |
| `--success` | `oklch(0.65 0.18 145)` | Online, healthy, passed |
| `--warning` | `oklch(0.75 0.15 85)` | Caution, degraded, high load |
| `--info` | `oklch(0.65 0.12 230)` | Informational, neutral |

### Surface Hierarchy

```
background (0.07) → card (0.12) → secondary (0.18) → accent (0.18+chroma)
```

Each level is a step up in lightness. Cards float above background. Interactive elements get slightly more chroma.

### Borders

| Token | Value | Usage |
|-------|-------|-------|
| `--border` | `oklch(1 0 0 / 6%)` | Default borders — barely visible |
| `--input` | `oklch(1 0 0 / 10%)` | Input borders — slightly more visible |

---

## Typography

### Fonts

| Variable | Family | Role |
|----------|--------|------|
| `--font-heading` | Cormorant Garamond (400, 500, 600, 700) | h1-h4, brand text, page titles |
| `--font-sans` | Inter | Body text, UI elements, labels |
| `--font-mono` | Geist Mono | Metrics, data, code, numbers |

### Scale

| Element | Font | Size | Weight | Tracking |
|---------|------|------|--------|----------|
| h1 (page title) | Cormorant | text-2xl (1.5rem) | semibold (600) | tracking-wide |
| h2 (section) | Cormorant | text-lg (1.125rem) | semibold (600) | — |
| h3 (card title) | Cormorant | text-sm (0.875rem) | medium (500) | — |
| Body | Inter | text-sm (0.875rem) | normal (400) | — |
| Label | Inter | text-xs (0.75rem) | medium (500) | — |
| Caption | Inter | text-xs (0.75rem) | normal (400) | text-muted-foreground |
| Data value | Geist Mono | text-xs (0.75rem) | medium (500) | — |
| Brand mark | Cormorant | text-xl (1.25rem) | semibold (600) | tracking-wide |

### Rules

- Headings (h1-h4) always use `font-heading` (Cormorant Garamond) via the CSS base layer rule.
- Numeric data (temperatures, VRAM, power, percentages) uses `font-mono`.
- Never use Cormorant below text-sm — it doesn't read well at tiny sizes.
- `tracking-wide` only on brand text and page-level headings.

---

## Spacing

Uses Tailwind's default 4px base scale. Key decisions:

| Context | Value | Tailwind |
|---------|-------|----------|
| Page padding | 24px | `p-6` |
| Card internal padding | 24px | `p-6` (via shadcn Card) |
| Card header gap | 8px | `pb-2` |
| Section gap | 24px | `space-y-6` |
| Card grid gap | 16px | `gap-4` |
| Compact item gap | 8px | `gap-2` |
| Inline element gap | 6px | `gap-1.5` |
| Sidebar width | 224px | `w-56` |

### Layout

- Fixed sidebar (56 = 224px) on left
- Main content: `ml-56 min-h-screen p-6`
- Primary grid: 5 columns at lg+ (`lg:grid-cols-5`)
- GPU grid: 5 columns for 5+ GPUs, 2 columns for fewer

---

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Small buttons, badges |
| `--radius-md` | 8px | Buttons, inputs |
| `--radius-lg` | 10px | Cards, dialogs |
| `--radius-xl` | 14px | Large containers |
| `rounded-full` | 9999px | Progress bars, status dots |

---

## Status Indicators

### GPU Load (3-tier)

| Range | Color | Tailwind |
|-------|-------|----------|
| 0-50% | Green | `bg-green-500` / `text-green-400` |
| 51-80% | Yellow | `bg-yellow-500` / `text-yellow-400` |
| 81-100% | Red | `bg-red-500` / `text-red-400` |

### Temperature (3-tier)

| Range | Color | Tailwind |
|-------|-------|----------|
| < 65C | Green | `text-green-400` |
| 65-80C | Yellow | `text-yellow-400` |
| > 80C | Red | `text-red-400` |

### Service Health

| State | Indicator |
|-------|-----------|
| Online | `bg-green-500` dot (1.5px-3px) |
| Offline | `bg-red-500` dot |
| Degraded | `bg-yellow-500` dot |

---

## Components

### Card

Base shadcn Card with Athanor overrides. `bg-card` surface, `border-border` edges.

```tsx
<Card>
  <CardHeader className="pb-2">
    <CardTitle className="text-sm">Section Name</CardTitle>
  </CardHeader>
  <CardContent>...</CardContent>
</Card>
```

### Badge

CVA variants: `default` (amber fill), `outline` (border only), `destructive`, `secondary`, `ghost`.

### GpuCard

Compact and full modes. Compact for overview grids, full for detail views. Always uses `font-mono` for metrics.

### ProgressBar

Thin (`h-1.5`), rounded-full, color-coded by value. Red >80%, Yellow 50-80%, Green below.

### Sparkline

Inline SVG, configurable color/fill. 1.5px stroke, 10% opacity fill.

---

## Icon System

Inline SVG icons in the sidebar (8 icons). No icon library dependency at runtime — keeps bundle small. Stroke-based, 24x24 viewBox, `currentColor`, `strokeWidth="2"`.

When adding new icons, follow the same pattern: functional component, `className` prop, `h-4 w-4` default size.

---

## Interaction States

| State | Treatment |
|-------|-----------|
| Hover | `bg-accent` (subtle background shift) |
| Focus | `ring-ring/50` (3px amber ring at 50% opacity) |
| Active | `bg-primary text-primary-foreground` |
| Disabled | `opacity-50 pointer-events-none` |
| Loading | Pulse animation or skeleton (tbd) |

---

## Chart Colors

5-color sequential palette for data visualization:

1. `oklch(0.75 0.08 65)` — Amber (primary, always first)
2. `oklch(0.65 0.12 160)` — Teal
3. `oklch(0.55 0.1 230)` — Blue
4. `oklch(0.7 0.1 330)` — Magenta
5. `oklch(0.6 0.06 90)` — Olive

Amber first. Warm tones preferred. Cool tones for contrast when needed.

---

## Responsive Strategy

| Breakpoint | Layout |
|------------|--------|
| < 1024px | Single column, sidebar collapses (tbd) |
| >= 1024px (lg) | Full sidebar + multi-column grid |
| >= 1280px (xl) | Wider cards, more data visible |

Currently optimized for desktop (1920x1080+). Mobile responsive is future work.

---

## Anti-Patterns

- **No bright neons.** No saturated cyan, lime, or hot pink.
- **No gray backgrounds.** Background is black (0.07), not gray (0.2+).
- **No generic shadcn defaults.** Every color was customized for Athanor.
- **No decorative gradients.** Flat surfaces. Depth comes from lightness hierarchy only.
- **No rounded-3xl+ on small elements.** Large radii are for modals/overlays only.
- **No emoji in UI.** Activity feed uses them temporarily — replace with proper icons.
