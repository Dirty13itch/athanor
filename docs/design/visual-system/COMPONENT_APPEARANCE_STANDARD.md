# Component Appearance Standard

## Purpose

This document defines how shared UI primitives should look under the new Athanor visual system.

The goal is to remove route-by-route guesswork.

## Surface families

### 1. Chrome surfaces

Used for:

- sidebar
- top header
- mobile nav sheet
- command palette frame

Rules:

- darkest stable material after page background
- low internal contrast
- stronger border discipline than content panels
- limited accent use

### 2. Panel surfaces

Used for:

- main content cards
- route sections
- grouped operator blocks

Rules:

- readable at long duration
- modest contrast from page background
- softer shadow than hero/overlay surfaces

### 3. Instrument surfaces

Used for:

- charts
- metrics
- telemetry wells
- compact state tiles

Rules:

- denser
- quieter
- less decorative than general panels
- optimized for numbers and small labels

### 4. Hero/spotlight surfaces

Used for:

- command-center attention lane
- system map hero blocks
- major governance cards

Rules:

- allowed richer material contrast
- may use domain accent trims
- may use stronger edge light
- still subordinate to severity rules

### 5. Overlay surfaces

Used for:

- dialogs
- drawers
- sheets

Rules:

- higher elevation
- softer translucency allowed
- edge lighting stronger than normal panels
- content density still operational, not decorative

## Cards

### Standard cards

- Use panel surfaces
- Title and body spacing should prioritize scanability
- Do not use decorative color fields
- Use status or domain color only as trim, badge, icon, or subtle header cue

### Metric cards

- Use instrument surfaces
- Numeric value dominates
- Label is uppercase or small-caps style metadata
- Supporting text is short and muted
- Trend or delta treatment must be consistent

### Spotlight cards

- Use hero surfaces
- Reserved for truly important command-center modules
- At most 1-2 spotlight cards per viewport cluster

## Navigation

### Sidebar links

- Idle state should be quiet, not ghosted into illegibility
- Active state should use structural accent with material change, not only text color
- Hover should use neutral state treatment, not domain coloring

### Tabs and segment controls

- Structural accent for active
- Domain trims allowed only when the route family owns that domain color
- Never encode status solely by selected tab color

## Status indicators

### Dots

Use only for:

- health
- warning
- failure
- paused
- review

Rules:

- consistent semantic mapping across routes
- inactive or unknown states should use neutral/paused grammar, not ad hoc gray guesses

### Badges

Badge types:

- semantic status badge
- neutral metadata badge
- domain badge
- action/context badge

Rules:

- status badge and domain badge must look different enough to prevent confusion
- severe states should be unmistakable

## Charts

### Line charts

- single-series trend should default to sequential blue/cyan scale
- alert overlays should use severity colors only when they truly indicate operational state

### Comparison charts

- follow fixed categorical order
- avoid reassigning colors by route

### Thresholds

- threshold lines use status colors, not category colors

### Legends

- direct labels preferred where feasible
- legends simplified for dashboard density

## Tables and dense lists

- prioritize row clarity and scanability
- use typography and separators first
- use color only for meaningful state
- avoid full-row tinting except for critical escalation or explicit selection

## Dialogs, drawers, and sheets

- must visually separate from the route behind them
- should feel slightly more refined than route panels
- should not introduce a different aesthetic language

## Agent-specific surfaces

### Crew / agent summary

- domain or lane identity can appear in a contained way
- status should dominate over personality styling

### Agent detail

- visually separate:
  - current run
  - recent outputs
  - provider/lease posture
  - judge status
  - failure state

## Command center modules

Command-center modules should follow a three-band grammar:

1. command / posture
2. action / intervention
3. evidence / recent context

Visual hierarchy should reinforce those bands.

## Empty, loading, degraded, and error states

### Empty

- low drama
- clear next action
- no severity colors

### Loading

- neutral motion and neutral signal
- no alarming color

### Degraded

- warning grammar
- show partial usefulness where possible

### Error

- danger grammar
- clear retry or escape path

## Mobile-specific rules

- compact cards must preserve hierarchy, not simply shrink everything
- metrics must remain legible at one-hand scanning distance
- dense badges and chips must wrap gracefully
- charts may simplify legends and axes on mobile

## What to retire

Retire these visual habits:

- atmospheric warm glows as general shell treatment
- literary headings on technical panels
- ad hoc card variants created per route
- mixed status/domain badge semantics
- route-local chart palettes
