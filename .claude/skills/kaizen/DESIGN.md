# Design Refinement Loop — UI/UX Perpetual Polish

*Every pixel should earn its place. If it doesn't communicate, it's noise.*

## The Design Loop

```
LOOK → FEEL → IDENTIFY → REFINE → VERIFY → SHIP → LOOK AGAIN
```

## Step 1: LOOK — Experience the Page

Don't read the code first. Look at the page as a user would:
- Curl the page or open it in browser
- Screenshot if possible (use Chrome DevTools MCP)
- Ask: What does my eye go to FIRST? Is that the right thing?
- Ask: What's confusing? What's redundant? What's missing?
- Ask: Does it feel premium or prototype?

## Step 2: FEEL — Emotional Response

The UI should evoke specific feelings:
- **Confidence** — "The system is working and I can see it"
- **Control** — "I know what's happening and can change it"
- **Craft** — "Someone cared deeply about this"
- **Calm** — "No alarm bells unless something is actually wrong"

If a page feels chaotic, cluttered, or confusing — that's the target.

## Step 3: IDENTIFY — What Breaks the Feeling?

Common UI problems ranked by impact:

### Signal-to-Noise
- [ ] Is color used ONLY for meaning? (green=good, amber=attention, red=bad)
- [ ] Are there decorative icons that don't communicate state? → Remove or mute them
- [ ] Is every card/section necessary? → Collapse or remove if not
- [ ] Are labels competing with values? → Labels should whisper, values should speak

### Contrast & Hierarchy
- [ ] Can you read everything at arm's length? → Increase contrast
- [ ] Is there a clear visual hierarchy? → One thing should be biggest/brightest
- [ ] Are key numbers in `font-mono font-bold`? → They should be
- [ ] Is secondary text clearly secondary? → Use `text-muted-foreground/60`

### Spacing & Rhythm
- [ ] Is spacing consistent? → Use 4px grid (gap-1=4px, gap-2=8px, gap-3=12px, gap-4=16px)
- [ ] Do cards have breathing room? → `p-4` minimum on desktop
- [ ] Are section gaps consistent? → `gap-6` between zones, `gap-3` within
- [ ] Does the page feel cramped or airy? → Aim for "confident density"

### Responsiveness
- [ ] Does it work at 375px? → Stack columns, shrink text, scroll horizontally only for data
- [ ] Does it work at 768px? → 2 columns max
- [ ] Does it work at 1920px? → Full layout, nothing stretched
- [ ] Touch targets >= 44px on mobile?

### Motion & State
- [ ] Do loading states exist? → Skeleton screens or spinners
- [ ] Do active items pulse or animate? → Subtle, 1-2s duration
- [ ] Do transitions feel smooth? → `transition-all duration-300`
- [ ] Does the ambient glow reflect system state? → Use `--system-intensity`

### Color Semantics (THE RULES)
```
GREEN  → Healthy, active, success, running, connected
AMBER  → Warning, degraded, needs attention, moderate load
RED    → Error, failed, critical, broken, disconnected
WHITE  → Primary values, key metrics, important text
GRAY   → Labels, descriptions, secondary info, chrome
ACCENT → Active lens identity (oklch per-lens color)
DOMAIN → Agent identity colors (creative=pink, media=teal, etc.)
```

Nothing else gets color. If something has color and doesn't fit these categories, it's noise. Remove it.

### Typography Scale
```
text-3xl font-mono font-bold  → Hero metric (one per page max)
text-2xl font-mono font-bold  → Key value (stat cards)
text-lg font-semibold         → Section title
text-base font-medium         → Card title, important label
text-sm                       → Body text, descriptions
text-xs text-muted-foreground → Metadata, timestamps, secondary labels
text-xs uppercase tracking-wide text-muted-foreground/60 → Category labels
```

## Step 4: REFINE — Surgical Edits

- Change ONE thing at a time
- Prefer CSS/Tailwind class changes over structural changes
- Use the existing design tokens (surface-*, signal-*, oklch)
- Don't add new colors — use the ones that exist more carefully
- When in doubt: remove, don't add

## Step 5: VERIFY

- TypeScript clean
- Looks right at 375px, 768px, 1920px
- Signal colors match their meaning
- Key info is highest contrast
- No horizontal scroll at mobile widths

## Step 6: SHIP — Deploy to Workshop

Same as kaizen: scp, build, deploy, verify live.

## Step 7: LOOK AGAIN — Start Over

The loop never ends. Every page, every component, every interaction can be better.

## Page Priority Order

Start with the most-visited pages:
1. `/home` (Command Center) — THE experience
2. `/gallery` — Where Shaun reviews creative output
3. `/agents` — Agent interaction hub
4. `/chat` — Conversational interface
5. `/gpu` — Hardware monitoring
6. `/tasks` — Work tracking
7. `/media` — Media library management
8. `/services` — Service health
9. `/monitoring` — Cluster metrics
10. Everything else

## The North Star

The dashboard should feel like a **premium cockpit** — every dial, every indicator, every number is there because it matters. Nothing is decorative. Nothing is accidental. The system's state is communicated through color, size, position, and motion. When you look at it, you KNOW what's happening in 2 seconds.

If it takes longer than 2 seconds to understand the system state, the design has failed.
